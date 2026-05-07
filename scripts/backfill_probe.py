#!/usr/bin/env python3
"""Backfill probe — diagnose inconsistencies between sync-manifest and DJEN proxy.

Pulls the canonical manifest from IA, samples entries by category
(absent / unknown / available / 403 / timeout), re-probes the DJEN proxy live,
and prints a side-by-side comparison so we can spot rows where the manifest
disagrees with reality.

Designed to run inside the ``backfill-probe`` GitHub Actions workflow. The job
intentionally exits non-zero at the end so the run is flagged as failed and
the operator gets the report attached to a visible failure.
"""

from __future__ import annotations

import asyncio
import csv
import io
import os
import random
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx


MANIFEST_URL = "https://archive.org/download/causaganha-dashboard/sync-manifest.csv"
DJEN_PROXY_FALLBACK = "https://djen-proxy-mhgmawcn3a-rj.a.run.app"

SAMPLE_PER_CATEGORY = 8
CONCURRENCY = 6
HTTP_TIMEOUT = 30.0


def _proxy_base() -> str:
    return os.environ.get("DJEN_PROXY_URL", "").strip() or DJEN_PROXY_FALLBACK


def _ia_auth_header() -> str | None:
    access = os.environ.get("IAS3_ACCESS_KEY", "").strip()
    secret = os.environ.get("IAS3_SECRET_KEY", "").strip()
    if not access or not secret:
        return None
    return f"LOW {access}:{secret}"


async def _fetch_manifest(client: httpx.AsyncClient) -> list[dict[str, str]]:
    """Download sync-manifest.csv from IA and parse it."""
    headers: dict[str, str] = {}
    auth = _ia_auth_header()
    if auth:
        headers["Authorization"] = auth

    resp = await client.get(MANIFEST_URL, headers=headers, timeout=120.0)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    return list(reader)


def _classify(djen_raw: str) -> str:
    raw = (djen_raw or "").strip()
    if raw == "":
        return "unknown"
    if raw == "200":
        return "available"
    if raw in {"404", "400"}:
        return "absent"
    if raw == "403":
        return "rate-limited"
    if raw in {"timeout", "network"}:
        return "transient"
    return f"other:{raw}"


async def _probe_one(
    client: httpx.AsyncClient,
    tribunal: str,
    d: str,
    sem: asyncio.Semaphore,
) -> dict[str, Any]:
    """Hit the DJEN proxy live for a single (tribunal, date) and capture result."""
    base = _proxy_base()
    url = f"{base}/api/v1/caderno/{tribunal}/{d}/D"
    out: dict[str, Any] = {
        "tribunal": tribunal,
        "date": d,
        "url": url,
        "status": None,
        "live_raw": None,
        "snippet": None,
        "error": None,
    }
    async with sem:
        try:
            resp = await client.get(url, timeout=HTTP_TIMEOUT)
        except httpx.TimeoutException:
            out["live_raw"] = "timeout"
            return out
        except httpx.RequestError as exc:
            out["live_raw"] = "network"
            out["error"] = f"{type(exc).__name__}: {exc}"
            return out

        out["status"] = resp.status_code
        out["live_raw"] = str(resp.status_code)
        body = resp.text or ""
        out["snippet"] = body[:240]
        return out


def _diff_label(manifest_raw: str, live_raw: str | None) -> str:
    m_cat = _classify(manifest_raw)
    live_cat = _classify(live_raw or "")
    if m_cat == live_cat:
        return "match"
    return f"DRIFT manifest={m_cat}({manifest_raw or 'empty'}) live={live_cat}({live_raw})"


def _sample_by_category(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        cat = _classify(r.get("djen_raw", ""))
        buckets[cat].append(r)
    sampled: dict[str, list[dict[str, str]]] = {}
    rng = random.Random(0xC4)  # noqa: S311 — sampling for diagnostics, not crypto
    for cat, items in buckets.items():
        rng.shuffle(items)
        sampled[cat] = items[:SAMPLE_PER_CATEGORY]
    return sampled


def _print_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


async def main() -> int:
    started = datetime.now(UTC).isoformat()
    proxy = _proxy_base()
    auth_present = _ia_auth_header() is not None

    _print_header("BACKFILL PROBE — config")
    print(f"started_utc:    {started}")
    print(f"proxy_base:     {proxy}")
    print(f"manifest_url:   {MANIFEST_URL}")
    print(f"ia_auth_set:    {auth_present}")
    print(f"sample/cat:     {SAMPLE_PER_CATEGORY}")
    print(f"concurrency:    {CONCURRENCY}")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        _print_header("Fetching manifest from IA")
        try:
            rows = await _fetch_manifest(client)
        except httpx.HTTPError as exc:
            print(f"FATAL: manifest fetch failed: {exc!r}", file=sys.stderr)
            return 2

        total = len(rows)
        cat_counts = Counter(_classify(r.get("djen_raw", "")) for r in rows)
        ia_status_counts = Counter((r.get("ia_status") or "").strip() for r in rows)

        print(f"manifest_rows:  {total}")
        print("djen_raw breakdown:")
        for cat, n in sorted(cat_counts.items(), key=lambda kv: -kv[1]):
            print(f"  {cat:20s} {n:>8d}")
        print("ia_status breakdown:")
        for st, n in sorted(ia_status_counts.items(), key=lambda kv: -kv[1]):
            print(f"  {st or '<empty>':20s} {n:>8d}")

        # ── Backlog liveness: is updated_at moving? ─────────────────────────
        # If unknowns are being processed, their updated_at should be recent.
        # Stale updated_at on unknowns means workers aren't touching them.
        now = datetime.now(UTC)
        age_buckets: dict[str, Counter[str]] = {
            "unknown": Counter(),
            "available": Counter(),
            "absent": Counter(),
        }

        def _age_label(ts: str) -> str:
            ts = (ts or "").strip()
            if not ts:
                return "never"
            normalized = ts.removesuffix("Z") + "+00:00" if ts.endswith("Z") else ts
            try:
                parsed = datetime.fromisoformat(normalized)
            except ValueError:
                return "unparseable"
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            delta = now - parsed
            if delta < timedelta(hours=1):
                return "<1h"
            if delta < timedelta(days=1):
                return "<1d"
            if delta < timedelta(days=7):
                return "<7d"
            if delta < timedelta(days=30):
                return "<30d"
            if delta < timedelta(days=90):
                return "<90d"
            return ">=90d"

        most_recent: dict[str, str] = {"unknown": "", "available": "", "absent": ""}
        for r in rows:
            cat = _classify(r.get("djen_raw", ""))
            if cat in age_buckets:
                ts = (r.get("updated_at") or "").strip()
                age_buckets[cat][_age_label(ts)] += 1
                if ts and ts > most_recent[cat]:
                    most_recent[cat] = ts

        print()
        print("updated_at age (per category):")
        order = ["<1h", "<1d", "<7d", "<30d", "<90d", ">=90d", "never", "unparseable"]
        header = "  category    " + "".join(f"{b:>10s}" for b in order) + "   most_recent"
        print(header)
        for cat in ("unknown", "available", "absent"):
            row = f"  {cat:11s} " + "".join(f"{age_buckets[cat].get(b, 0):>10d}" for b in order)
            row += f"   {most_recent[cat] or '-'}"
            print(row)
        print(
            "  → If `unknown` shows little activity in <1h/<1d/<7d, "
            "the backlog is NOT being processed at any meaningful rate."
        )

        sampled = _sample_by_category(rows)
        _print_header("Probing samples against DJEN proxy")

        sem = asyncio.Semaphore(CONCURRENCY)
        tasks: list[asyncio.Task[dict[str, Any]]] = []
        plan: list[tuple[str, dict[str, str]]] = []
        for cat, items in sampled.items():
            for r in items:
                trib = (r.get("tribunal") or "").strip()
                d = (r.get("date") or "").strip()
                if not trib or not d:
                    continue
                plan.append((cat, r))
                tasks.append(asyncio.create_task(_probe_one(client, trib, d, sem)))

        results = await asyncio.gather(*tasks, return_exceptions=False)

        drift_rows: list[str] = []
        match_count = 0
        for (cat, r), res in zip(plan, results, strict=True):
            manifest_raw = r.get("djen_raw", "")
            live_raw = res.get("live_raw")
            label = _diff_label(manifest_raw, live_raw)
            line = (
                f"[{cat:13s}] {res['tribunal']:>6s} {res['date']} "
                f"manifest_raw={manifest_raw!r:>10s} live={live_raw!r:>10s} "
                f"http={res['status']!s:>5s} :: {label}"
            )
            print(line)
            if res.get("error"):
                print(f"    error: {res['error']}")
            if res.get("snippet") and (
                label.startswith("DRIFT") or cat in {"unknown", "transient"}
            ):
                snippet = res["snippet"].replace("\n", " ")[:200]
                print(f"    body: {snippet}")
            if label == "match":
                match_count += 1
            else:
                drift_rows.append(line)

        _print_header("DRIFT SUMMARY")
        print(f"probed:    {len(plan)}")
        print(f"matches:   {match_count}")
        print(f"drift:     {len(drift_rows)}")
        for d in drift_rows:
            print(f"  - {d}")

        # Bonus: probe a few "today/yesterday" samples to detect proxy rate-limit
        # patterns (CloudFront 403 vs healthy 200) — independent of manifest state.
        _print_header("Live proxy health check (recent dates)")
        today = datetime.now(UTC).date()
        yesterday = today - timedelta(days=1)
        recent_targets = [
            ("TJSP", today.isoformat()),
            ("TJRJ", today.isoformat()),
            ("TJSP", yesterday.isoformat()),
            ("TRF1", today.isoformat()),
        ]
        live_tasks = [asyncio.create_task(_probe_one(client, t, d, sem)) for t, d in recent_targets]
        for res in await asyncio.gather(*live_tasks):
            print(
                f"  {res['tribunal']:>6s} {res['date']} -> http={res['status']} "
                f"raw={res['live_raw']!r}"
            )

    _print_header("DONE — failing intentionally so the run is flagged")
    print("This probe is configured to exit 1 on success so its log is preserved.")
    print("If you want it to pass, remove the final `sys.exit(1)` in scripts/backfill_probe.py.")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
