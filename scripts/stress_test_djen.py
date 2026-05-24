#!/usr/bin/env python3
"""Stress test DJEN API to find rate limit threshold.

Sends increasing levels of concurrent requests to DJEN and reports
the response distribution (200 / 404 / 403 / timeout / error) at each
level. Stops when the error rate crosses a configurable threshold
(default 30%) or after the max concurrency.

Usage:
    uv run python scripts/stress_test_djen.py
    uv run python scripts/stress_test_djen.py --tribunal TJSP --max 100

The test uses dates known to exist on DJEN (recent business days) so
404s are genuine "no data" and not test artifacts. 403s indicate
CloudFront/WAF blocks — the rate limit signal we're looking for.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import time
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx


CONFIG_PATH = Path(__file__).parent.parent / "data" / "djen-safe-concurrency.json"


DJEN_BASE = "https://comunicaapi.pje.jus.br"

# Tribunals known to have data for many recent dates
DEFAULT_TRIBUNALS = [
    "TJSP",
    "TJBA",
    "TJMG",
    "TJRS",
    "TJPR",
    "TJCE",
    "TJDFT",
    "TJES",
    "TJMA",
    "TJRN",
    "TRF1",
    "TRF3",
    "TRF4",
    "TRT1",
    "TST",
]


def business_days(end: date, count: int) -> list[date]:
    """Return the last N business days ending at `end`."""
    days = []
    d = end
    while len(days) < count:
        if d.weekday() < 5:  # Mon-Fri
            days.append(d)
        d -= timedelta(days=1)
    return days


async def probe(
    client: httpx.AsyncClient,
    tribunal: str,
    day: date,
) -> tuple[str, float]:
    """Make one DJEN request, return (status_code_or_category, latency_s)."""
    url = f"{DJEN_BASE}/api/v1/caderno/{tribunal}/{day.isoformat()}/D"
    start = time.monotonic()
    try:
        resp = await client.get(url, timeout=15)
        return str(resp.status_code), time.monotonic() - start
    except httpx.TimeoutException:
        return "timeout", time.monotonic() - start
    except (httpx.HTTPError, httpx.RequestError) as exc:
        return f"err:{type(exc).__name__}", time.monotonic() - start


async def run_burst(
    concurrency: int,
    total_requests: int,
    tribunals: list[str],
    days: list[date],
) -> tuple[Counter, list[float], float]:
    """Fire `total_requests` with `concurrency` in-flight. Return stats."""
    sem = asyncio.Semaphore(concurrency)
    results: list[tuple[str, float]] = []
    rng = random.Random(42)  # noqa: S311 — not cryptographic, just reproducible picks

    async with httpx.AsyncClient(follow_redirects=True) as client:

        async def _one() -> None:
            async with sem:
                t = rng.choice(tribunals)
                d = rng.choice(days)
                results.append(await probe(client, t, d))

        start = time.monotonic()
        await asyncio.gather(*[_one() for _ in range(total_requests)])
        elapsed = time.monotonic() - start

    statuses = Counter(s for s, _ in results)
    latencies = [lat for _, lat in results]
    return statuses, latencies, elapsed


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(int(len(s) * p / 100), len(s) - 1)
    return s[idx]


def print_result(
    concurrency: int,
    statuses: Counter,
    latencies: list[float],
    elapsed: float,
    total: int,
) -> float:
    """Print one row and return error rate (0.0-1.0)."""
    rps = total / elapsed if elapsed > 0 else 0
    errors = sum(
        c for s, c in statuses.items() if s in {"403", "timeout"} or s.startswith(("err:", "5"))
    )
    err_rate = errors / total if total else 0

    status_str = " ".join(f"{k}:{v}" for k, v in sorted(statuses.items()))
    print(
        f"  conc={concurrency:>3}  reqs={total:>3}  "
        f"{elapsed:>5.1f}s  "
        f"rps={rps:>5.1f}  "
        f"p50={percentile(latencies, 50) * 1000:>5.0f}ms  "
        f"p95={percentile(latencies, 95) * 1000:>5.0f}ms  "
        f"err={err_rate * 100:>4.1f}%  {status_str}"
    )
    return err_rate


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tribunal", help="Single tribunal (default: mix of 15)")
    parser.add_argument("--min", type=int, default=2, help="Min concurrency")
    parser.add_argument("--max", type=int, default=32, help="Max concurrency")
    parser.add_argument(
        "--reqs-per-level",
        type=int,
        default=200,
        help="Requests per concurrency level (need enough to surface 403s)",
    )
    parser.add_argument(
        "--err-threshold",
        type=float,
        default=0.1,
        help="Stop when error rate exceeds this (0.0-1.0)",
    )
    parser.add_argument(
        "--cooldown",
        type=float,
        default=10.0,
        help="Seconds between levels (let WAF cool down)",
    )
    args = parser.parse_args()

    tribunals = [args.tribunal] if args.tribunal else DEFAULT_TRIBUNALS
    today = datetime.now(UTC).date()
    days = business_days(today - timedelta(days=2), 30)

    print(f"DJEN stress test starting at {today.isoformat()}")
    print(f"Tribunals: {','.join(tribunals)}")
    print(f"Date pool: {days[-1]} to {days[0]} ({len(days)} business days)")
    print(f"Requests per level: {args.reqs_per_level}, cooldown: {args.cooldown}s")
    print(f"Stop threshold: {args.err_threshold * 100:.0f}% error rate\n")

    # Geometric-ish progression: 1, 2, 4, 8, 16, 32, 64...
    levels = []
    c = args.min
    while c <= args.max:
        levels.append(c)
        c = max(c + 1, c * 2)

    for i, concurrency in enumerate(levels):
        statuses, latencies, elapsed = await run_burst(
            concurrency, args.reqs_per_level, tribunals, days
        )
        err_rate = print_result(concurrency, statuses, latencies, elapsed, args.reqs_per_level)

        if err_rate >= args.err_threshold:
            safe = levels[max(0, i - 1)]
            print(f"\n[WARNING] Error rate {err_rate * 100:.1f}% crossed threshold — stopping.")
            print(f"   Safe concurrency: ~{safe}")
            _save_config(safe, err_threshold=args.err_threshold)
            return

        if i < len(levels) - 1:
            await asyncio.sleep(args.cooldown)

    safe = levels[-1]
    print("\n[SUCCESS] Max concurrency reached without crossing error threshold.")
    print(f"   Safe concurrency: >= {safe}")
    _save_config(safe, err_threshold=args.err_threshold)


def _save_config(safe_concurrency: int, err_threshold: float) -> None:
    """Persist the discovered safe concurrency for the engine to pick up."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(
            {
                "safe_concurrency": safe_concurrency,
                "err_threshold": err_threshold,
                "measured_at": datetime.now(UTC).isoformat(timespec="seconds"),
            },
            indent=2,
        )
    )
    print(f"   -> saved to {CONFIG_PATH.relative_to(Path.cwd())}")


if __name__ == "__main__":
    asyncio.run(main())
