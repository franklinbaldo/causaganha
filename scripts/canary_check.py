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
3. Reachability/structure of the public stj_totals.json artifact. STJ has no
   per-pair manifest like DJEN, so this proves only that the pipeline still
   produces a non-empty, well-formed artifact — not freshness (see #892).
4. Reachability/structure of the TJRO JURIS crawl/upload manifest
   (tjro-juris-manifest.csv). This proves only that the pipeline's own
   authoritative manifest is populated, not that those documents have
   reached the reconciled catalog (juris_totals.json is currently empty —
   see #924 3.1, a separate reconciliation gap this canary does not cover).
5. Reachability/structure of the published DataJud coherent state bundle
   (datajud-state-{tribunal}.zip) — the same bundle ephemeral runners
   restore before continuing the pipeline (#888/#889). No freshness SLO:
   enrichment cadence is rate-limit-bound, not a fixed interval like DJEN's
   daily sync, so this proves reachability/structure only (see #892).

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

from datajud import state as datajud_state
from datajud.manifest import ManifestDataJud
from datajud.manifest import ManifestFormatError as DataJudManifestFormatError
from djen_backup.djen import DJENNotFoundError, DJENRateLimitedError, get_caderno_url
from tjro_juris import archive as tjro_juris_archive
from tjro_juris.manifest import ManifestFormatError as TjroJurisManifestFormatError
from tjro_juris.manifest import ManifestJuris


log = structlog.get_logger()

SITE_STATUS_URL = "https://franklinbaldo.github.io/causaganha/data/site-status.json"
STJ_TOTALS_URL = "https://franklinbaldo.github.io/causaganha/data/stj_totals.json"

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


def check_stj_published() -> tuple[list[str], list[str]]:
    """Return (failures, warnings) from the public stj_totals.json artifact.

    STJ has no per-pair manifest to derive a freshness SLO from (unlike DJEN),
    so this proves only reachability and non-empty structure — matching #892's
    guidance to not turn a source limitation into a false operational promise.
    """
    failures: list[str] = []
    warnings: list[str] = []

    try:
        resp = httpx.get(STJ_TOTALS_URL, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        payload = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        failures.append(f"could not fetch/parse {STJ_TOTALS_URL}: {exc}")
        return failures, warnings

    total = payload.get("total")
    if total is None:
        failures.append("stj_totals.json missing 'total'")
    elif not total:
        failures.append("stj_totals.json total is zero/empty — STJ artifact looks empty")

    total_temas = payload.get("total_temas")
    if total_temas is None:
        failures.append("stj_totals.json missing 'total_temas'")

    if not payload.get("ultima_decisao"):
        failures.append("stj_totals.json missing 'ultima_decisao'")

    return failures, warnings


def check_tjro_juris_published() -> tuple[list[str], list[str]]:
    """Return (failures, warnings) from the public TJRO JURIS crawl/upload manifest.

    Proves only that the pipeline's own authoritative manifest
    (tjro-juris-manifest.csv) is reachable and structurally valid — the same
    authority `causaganha_status` reads, not the derived `juris_totals.json`
    catalog export, which is currently empty for an unrelated reason (#924
    3.1: reconciled documents never reached the public catalog). Matching
    #892's guidance, this does not claim the reconciliation gap is healthy.
    """
    failures: list[str] = []
    warnings: list[str] = []

    try:
        text = tjro_juris_archive.read_manifest_text()
    except httpx.HTTPError as exc:
        failures.append(f"could not fetch {tjro_juris_archive.MANIFEST_DOWNLOAD_URL}: {exc}")
        return failures, warnings

    if text is None:
        failures.append(
            f"{tjro_juris_archive.MANIFEST_DOWNLOAD_URL} returned 404 — "
            "no TJRO JURIS manifest published"
        )
        return failures, warnings

    try:
        manifest = ManifestJuris.load_text(text, source=tjro_juris_archive.MANIFEST_DOWNLOAD_URL)
    except TjroJurisManifestFormatError as exc:
        failures.append(f"TJRO JURIS manifest published but invalid: {exc}")
        return failures, warnings

    if not manifest.all_entries():
        failures.append("TJRO JURIS manifest is reachable but has zero entries")

    return failures, warnings


def check_datajud_published(tribunal: str = "tjro") -> tuple[list[str], list[str]]:
    """Return (failures, warnings) from the published DataJud coherent state bundle.

    Proves reachability and structural validity of `datajud-state-{tribunal}.zip`
    — the same bundle ephemeral runners restore before continuing the pipeline
    (#888/#889) — matching #892's guidance to prove only what the pipeline
    actually publishes. `read_remote_state` already fails closed
    (`RemoteStateError`) on transport errors, malformed bundles and checksum
    mismatches, so a single except clause here covers all of those. No
    freshness SLO: enrichment cadence is rate-limit-bound, not a fixed
    interval like DJEN's daily sync (see #892).
    """
    failures: list[str] = []
    warnings: list[str] = []

    try:
        published = datajud_state.read_remote_state(tribunal)
    except datajud_state.RemoteStateError as exc:
        failures.append(f"could not verify published DataJud state bundle: {exc}")
        return failures, warnings

    if published is None:
        failures.append(f"no coherent DataJud state bundle published for tribunal {tribunal!r}")
        return failures, warnings

    try:
        manifest = ManifestDataJud.load_text(
            published.manifest_text, source=datajud_state.bundle_name(tribunal)
        )
    except DataJudManifestFormatError as exc:
        failures.append(f"DataJud state bundle published but manifest is invalid: {exc}")
        return failures, warnings

    if not manifest.all_entries():
        failures.append("DataJud state bundle is reachable but manifest has zero entries")

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
    stj_failures, stj_warnings = check_stj_published()
    tjro_juris_failures, tjro_juris_warnings = check_tjro_juris_published()
    datajud_failures, datajud_warnings = check_datajud_published()

    failures = site_failures + djen_failures + stj_failures + tjro_juris_failures + datajud_failures
    warnings = site_warnings + djen_warnings + stj_warnings + tjro_juris_warnings + datajud_warnings

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
