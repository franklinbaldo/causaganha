#!/usr/bin/env python3
"""End-to-end canary — prove the deployed system works, not just that it builds.

CI (test.yml) validates the frontend build against synthetic stub data. It
never proves DJEN is reachable, the manifest pipeline is still running, or
the public dashboard reflects fresh data. This script closes that gap with
two independent checks against the real, deployed system:

1. Freshness/sanity of the public site-status.json (deployed dashboard data).
   The artifact itself must have been regenerated within 48h. Its
   `last_success_at` must reach the previous Brazilian business day, so a
   normal weekend does not page while a missed Monday is caught on Tuesday.
2. A single live DJEN lookup (get_caderno_url) for a stable tribunal on the
   most recent Brazilian business day, using the same client/proxy path
   production collection uses. Distinguishes "DJEN client is broken" from
   "no publication that day" (404/400) and from "rate limited" (403, a
   known-transient WAF response — logged as a warning, never a failure).

Exit 0 = all good (warnings allowed). Exit 1 = hard failure.

Usage:
    uv run python scripts/canary_check.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import structlog
from holidays import Brazil

from djen_backup.djen import DJENNotFoundError, DJENRateLimitedError, get_caderno_url


log = structlog.get_logger()

SITE_STATUS_URL = "https://franklinbaldo.github.io/causaganha/data/site-status.json"

# Maximum acceptable age for the deployed artifact itself. Source success
# uses a business-day deadline below instead of wall-clock hours.
FRESHNESS_THRESHOLD_HOURS = 48

# docs/SERVICE_OBJECTIVES.md declares a 24h publication→archive SLO, but
# site-status.json only exposes the aggregate pending_real count (pairs DJEN
# confirmed available but not yet uploaded to IA), not per-pair timestamps.
# This is a coarse proxy alarm on backlog size, not a literal delay
# measurement — live pending_real is normally 0, so any sustained backlog
# past this threshold is anomalous. Tune once real backlog episodes give a
# baseline.
PENDING_REAL_THRESHOLD = 50

# TJRO is the most-documented DJEN tribunal in this codebase (CLAUDE.md IA
# naming example, site_status.qmd worked example) — a stable, known-good
# canary target.
CANARY_TRIBUNAL = "TJRO"
MAX_PERCENT = 100

DJEN_DIRECT_URL = "https://comunicaapi.pje.jus.br"
DJEN_PROXY_FALLBACK_URL = "https://djen-proxy-mhgmawcn3a-rj.a.run.app"


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def _age_hours(ts: datetime | None, now: datetime) -> float | None:
    if ts is None:
        return None
    return (now - ts).total_seconds() / 3600


SATURDAY = 5  # date.weekday() >= SATURDAY means Sat/Sun


def last_business_day(today: date, br_holidays: Brazil) -> date:
    """Most recent day DJEN would plausibly have published (not weekend/holiday)."""
    d = today - timedelta(days=1)
    while d.weekday() >= SATURDAY or d in br_holidays:
        d -= timedelta(days=1)
    return d


def check_site_status(
    now: datetime, br_holidays: Brazil | None = None
) -> tuple[list[str], list[str]]:
    """Return (failures, warnings) from the public site-status.json."""
    failures: list[str] = []
    warnings: list[str] = []

    try:
        resp = httpx.get(SITE_STATUS_URL, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        payload = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        failures.append(f"could not fetch/parse {SITE_STATUS_URL}: {exc}")
        return failures, warnings

    generated_age = _age_hours(_parse_iso(payload.get("generated_at")), now)
    if generated_age is None:
        failures.append("site-status.json missing generated_at")
    elif generated_age > FRESHNESS_THRESHOLD_HOURS:
        failures.append(
            f"generated_at is {generated_age:.1f}h old (> {FRESHNESS_THRESHOLD_HOURS}h) "
            "— deploy-web pipeline appears stalled"
        )

    djen = payload.get("sources", {}).get("djen", {})
    success_at = _parse_iso(djen.get("last_success_at"))
    if success_at is None:
        failures.append("sources.djen.last_success_at missing or unparseable")
    else:
        holidays = br_holidays if br_holidays is not None else Brazil()
        expected_day = last_business_day(now.date(), holidays)
        if success_at.date() < expected_day:
            success_age = _age_hours(success_at, now)
            assert success_age is not None
            failures.append(
                f"sources.djen.last_success_at is {success_age:.1f}h old "
                f"and predates expected business day {expected_day} — sync engine "
                "stopped confirming successes even if the site still deploys"
            )

    coverage_pct = djen.get("coverage_pct")
    if coverage_pct is not None and not (0 <= coverage_pct <= MAX_PERCENT):
        failures.append(f"coverage_pct out of range: {coverage_pct}")
    if not djen.get("pairs_total"):
        failures.append("pairs_total is zero/missing — manifest looks empty")
    if not djen.get("tribunals_total"):
        failures.append("tribunals_total is zero/missing — manifest looks empty")

    pending_real = djen.get("pending_real")
    if pending_real is not None and pending_real > PENDING_REAL_THRESHOLD:
        failures.append(
            f"pending_real is {pending_real} (> {PENDING_REAL_THRESHOLD}) — "
            "publication→archive backlog growing, see docs/SERVICE_OBJECTIVES.md"
        )

    return failures, warnings


async def check_djen_live(target_date: date) -> tuple[list[str], list[str]]:
    """Return (failures, warnings) from one live DJEN lookup."""
    failures: list[str] = []
    warnings: list[str] = []

    base_url = DJEN_PROXY_FALLBACK_URL  # matches --use-proxy, the path GH runners use
    async with httpx.AsyncClient() as client:
        try:
            url = await get_caderno_url(client, base_url, CANARY_TRIBUNAL, target_date)
            log.info(
                "canary.djen.available",
                tribunal=CANARY_TRIBUNAL,
                date=str(target_date),
                url=url,
            )
        except DJENNotFoundError as exc:
            # Definitive absence (404/400/"Sem comunicações") — the client
            # correctly parsed a conclusive verdict. This is a PASS: it
            # proves the historically-buggy 200-without-URL path still
            # resolves to "absent", not a silent "available".
            log.info(
                "canary.djen.absent",
                tribunal=CANARY_TRIBUNAL,
                date=str(target_date),
                status_code=exc.status_code,
                reason=exc.reason,
            )
        except DJENRateLimitedError as exc:
            # 403 is documented as transient WAF rate-limiting, never proof
            # of an outage — warn, don't fail a single occurrence.
            warnings.append(f"DJEN rate-limited (403) on this single check: {exc}")
        except (httpx.HTTPError, ValueError) as exc:
            failures.append(f"DJEN live check failed unexpectedly: {exc}")

    return failures, warnings


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-file", default="/tmp/canary-report.json")
    args = parser.parse_args()

    now = datetime.now(UTC)
    br_holidays = Brazil()
    target_date = last_business_day(now.date(), br_holidays)

    site_failures, site_warnings = check_site_status(now, br_holidays)
    djen_failures, djen_warnings = await check_djen_live(target_date)

    failures = site_failures + djen_failures
    warnings = site_warnings + djen_warnings

    report = {
        "generated_at": now.isoformat(),
        "target_date": str(target_date),
        "tribunal": CANARY_TRIBUNAL,
        "failures": failures,
        "warnings": warnings,
    }
    Path(args.summary_file).write_text(json.dumps(report, indent=2))

    for w in warnings:
        log.warning("canary.warning", message=w)
    for f in failures:
        log.error("canary.failure", message=f)

    if failures:
        print(
            f"CANARY FAILED: {len(failures)} failure(s), {len(warnings)} warning(s)",
            file=sys.stderr,
        )
        return 1

    print(f"CANARY OK ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    import asyncio

    sys.exit(asyncio.run(main()))
