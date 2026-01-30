#!/usr/bin/env python3
"""Collect DJEN data and upload to Internet Archive.

This script downloads judicial communications from the DJEN API and uploads
them to Internet Archive for permanent archival.

Usage:
    # Collect recent data (default: last 7 days)
    python scripts/pipeline/collect.py

    # Collect specific date
    python scripts/pipeline/collect.py --date 2026-01-27

    # Collect specific tribunal
    python scripts/pipeline/collect.py --date 2026-01-27 --tribunal TJSP

    # Limit number of items
    python scripts/pipeline/collect.py --max-items 10

    # Control parallelism (default: 8 workers)
    python scripts/pipeline/collect.py --workers 8
"""

import argparse
import configparser
import hashlib
import json
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import httpx
import structlog

from causaganha.config import TRIBUNAIS

BACKFILL_PARQUET_URL = (
    "https://archive.org/download/causaganha-catalog/backfill-needed.parquet"
)


@dataclass
class AbsentReason:
    """Evidence for why a journal was marked absent."""

    status_code: int
    reason: str
    checked_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    response_snippet: str = ""


logger = structlog.get_logger()


def fetch_tribunais_from_api(proxy_url: str) -> list[str]:
    """Fetch current tribunal siglas from the DJEN API.

    Merges the API result with the known fallback list so we both
    auto-discover new courts and keep courts the listing omits.
    Falls back to TRIBUNAIS from config if the request fails.
    """
    url = f"{proxy_url}/api/v1/comunicacao/tribunal"
    try:
        resp = httpx.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        api_siglas: set[str] = set()
        for estado in data:
            for inst in estado.get("instituicoes", []):
                sigla = inst.get("sigla", "")
                if sigla:
                    api_siglas.add(sigla)
        # Merge: API may omit courts that still work (e.g. STF, some TREs),
        # and config may miss newly added courts.
        merged = sorted(api_siglas | set(TRIBUNAIS))
        logger.info(
            "tribunais_fetched",
            api_count=len(api_siglas),
            fallback_count=len(TRIBUNAIS),
            merged_count=len(merged),
        )
        return merged
    except Exception as exc:
        logger.warning("tribunais_fetch_failed", error=str(exc))
        return list(TRIBUNAIS)


def _fetch_ia_files_for_date(date_str: str) -> list[str]:
    """Fetch zip/absent filenames for a single date from IA metadata API.

    Uses the lightweight HTTP metadata endpoint (one request per date)
    instead of the heavy internetarchive library search which scans
    ALL items on every invocation.
    """
    item_id = f"djen-{date_str}"
    url = f"https://archive.org/metadata/{item_id}"
    try:
        resp = httpx.get(url, timeout=30)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return [
            f["name"]
            for f in data.get("files", [])
            if isinstance(f, dict) and f.get("name", "").endswith((".zip", ".absent"))
        ]
    except Exception:
        return []


def get_existing_files_for_dates(dates: list[str]) -> set[str]:
    """Get existing zip/absent files on IA for specific dates only.

    Queries the IA metadata HTTP API once per date. With backfill_days=7
    (weekdays only), this is ~5 requests — compared to the previous
    approach which scanned ALL djen-* items (hundreds of requests after
    months of data).
    """
    if not dates:
        return set()

    logger.info("checking_existing_files", dates_count=len(dates))
    existing: set[str] = set()

    with ThreadPoolExecutor(max_workers=min(4, len(dates))) as executor:
        futures = {executor.submit(_fetch_ia_files_for_date, d): d for d in dates}
        for future in as_completed(futures):
            try:
                for filename in future.result():
                    existing.add(filename)
            except Exception:
                pass

    logger.info("existing_files_found", count=len(existing), dates_checked=len(dates))
    return existing


def fetch_backfill_items() -> list[tuple[str, str]]:
    """Fetch missing (date, tribunal) pairs from the catalog, sorted d-1 first.

    Downloads backfill-needed.parquet from Internet Archive and returns items
    ordered by date descending so the most recent gaps are filled first.
    """
    try:
        con = duckdb.connect()
        con.execute("INSTALL httpfs; LOAD httpfs;")
        result = con.execute(
            f"""
            SELECT date, tribunal
            FROM read_parquet('{BACKFILL_PARQUET_URL}')
            ORDER BY date DESC
            """,
        ).fetchall()
        con.close()
        items = [(str(row[0]), str(row[1])) for row in result]
        logger.info("backfill_items_fetched", count=len(items))
        return items
    except Exception as exc:
        logger.warning("backfill_fetch_failed", error=str(exc))
        return []


def get_caderno_info(
    client: httpx.Client,
    proxy_url: str,
    tribunal: str,
    date_str: str,
    max_retries: int = 2,
) -> dict[str, Any] | AbsentReason | None:
    """Get caderno (journal) info from DJEN API.

    Args:
        client: Shared httpx client for connection pooling.
        proxy_url: Base URL of the DJEN proxy.
        tribunal: Court identifier (e.g. TJSP).
        date_str: Date in YYYY-MM-DD format.
        max_retries: Number of retries for transient (5xx/network) errors.

    Returns:
        dict: Success (journal data)
        AbsentReason: No journal for this day (with evidence)
        None: Transient error after retries exhausted
    """
    url = f"{proxy_url}/api/v1/caderno/{tribunal}/{date_str}/D"

    for attempt in range(max_retries + 1):
        try:
            response = client.get(url)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and (data.get("url") or data.get("items")):
                    return data
                return AbsentReason(
                    status_code=200,
                    reason="empty_response",
                    response_snippet=response.text[:200],
                )
            if response.status_code == 404:
                return AbsentReason(
                    status_code=404,
                    reason="not_found",
                )
            # 400/5xx: retry with backoff — DJEN proxy may be transiently broken
            if response.status_code == 400 or response.status_code >= 500:
                logger.warning(
                    "caderno_api_retryable_error",
                    tribunal=tribunal,
                    date=date_str,
                    status=response.status_code,
                    body=response.text[:200],
                    attempt=attempt + 1,
                )
                if attempt < max_retries:
                    time.sleep(2**attempt)
                    continue
                return None
            # Other client errors (403, 429, etc.) — don't retry
            logger.warning(
                "caderno_api_error",
                tribunal=tribunal,
                date=date_str,
                status=response.status_code,
                body=response.text[:200],
            )
            return None
        except Exception as e:
            logger.warning(
                "caderno_fetch_failed",
                tribunal=tribunal,
                date=date_str,
                error=str(e),
                attempt=attempt + 1,
            )
            if attempt < max_retries:
                time.sleep(2**attempt)
                continue
            return None
    return None


def download_zip(
    client: httpx.Client, url: str, output_path: Path, max_retries: int = 2,
) -> bool:
    """Download ZIP file from DJEN using streaming to reduce memory usage.

    Retries on server errors (5xx) and network failures with exponential
    backoff, matching the retry behavior of upload_to_ia and get_caderno_info.

    Args:
        client: Shared httpx client for connection pooling.
        url: Download URL for the ZIP file.
        output_path: Local path to write the downloaded file.
        max_retries: Number of retries for transient errors.
    """
    for attempt in range(max_retries + 1):
        try:
            with client.stream("GET", url) as response:
                if response.status_code != 200:
                    if response.status_code >= 500 and attempt < max_retries:
                        logger.warning(
                            "download_server_error",
                            url=url[:100],
                            status=response.status_code,
                            attempt=attempt + 1,
                        )
                        time.sleep(2**attempt)
                        continue
                    return False
                with output_path.open("wb") as f:
                    for chunk in response.iter_bytes(chunk_size=65536):
                        f.write(chunk)
            # Verify file size
            if output_path.stat().st_size < 100:
                logger.warning("file_too_small", path=str(output_path))
                output_path.unlink()
                return False
            return True
        except Exception as e:
            logger.warning(
                "download_failed",
                url=url[:100],
                error=str(e),
                attempt=attempt + 1,
            )
            if output_path.exists():
                output_path.unlink()
            if attempt < max_retries:
                time.sleep(2**attempt)
                continue
            return False
    return False


_IA_S3_URL = "https://s3.us.archive.org"


def _get_ia_s3_auth() -> str | None:
    """Get IA S3 authorization header value from env vars or config file."""
    access = os.environ.get("IAS3_ACCESS_KEY", "")
    secret = os.environ.get("IAS3_SECRET_KEY", "")
    if access and secret:
        return f"LOW {access}:{secret}"
    # Fall back to config file (created by CI workflow)
    config_path = Path.home() / ".config" / "internetarchive" / "ia.ini"
    if config_path.exists():
        cfg = configparser.ConfigParser()
        cfg.read(config_path)
        access = cfg.get("s3", "access", fallback="")
        secret = cfg.get("s3", "secret", fallback="")
        if access and secret:
            return f"LOW {access}:{secret}"
    return None


def _compute_md5(file_path: Path) -> str:
    """Compute hex-encoded MD5 checksum (IA S3 format)."""
    h = hashlib.md5()  # noqa: S324  — integrity check, not security
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def upload_to_ia(
    client: httpx.Client,
    item_id: str,
    file_path: Path,
    date_str: str,
) -> bool:
    """Upload file to Internet Archive via the S3-compatible API.

    Uses a shared httpx client for connection pooling across workers,
    with streaming upload and MD5 integrity verification.
    """
    filename = file_path.name
    url = f"{_IA_S3_URL}/{item_id}/{filename}"
    content_md5 = _compute_md5(file_path)

    headers = {
        "Content-MD5": content_md5,
        "x-archive-auto-make-bucket": "1",
        "x-archive-queue-derive": "0",
        "x-archive-meta-collection": "opensource",
        "x-archive-meta-mediatype": "data",
        "x-archive-meta-title": f"DJEN Data - {date_str}",
        "x-archive-meta-description": (
            "Diario de Justica Eletronico Nacional - Judicial communications from Brazilian courts."
        ),
        "x-archive-meta-subject": "brazilian-law;djen;legal;judiciary;open-data",
        "x-archive-meta-creator": "CausaGanha",
        "x-archive-meta-date": date_str,
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            with file_path.open("rb") as f:
                response = client.put(url, content=f, headers=headers)
            if response.is_success:
                return True
            logger.warning(
                "upload_http_error",
                item_id=item_id,
                file=filename,
                status=response.status_code,
                attempt=attempt + 1,
            )
            if response.status_code < 500:
                return False  # Client error — don't retry
        except Exception as e:
            logger.warning(
                "upload_error",
                item_id=item_id,
                error=str(e),
                attempt=attempt + 1,
            )
        if attempt < max_retries - 1:
            time.sleep(5 * (attempt + 1))
    return False


def _process_item(  # noqa: PLR0913
    api_client: httpx.Client,
    dl_client: httpx.Client,
    upload_client: httpx.Client,
    proxy_url: str,
    date_str: str,
    tribunal: str,
) -> str:
    """Process a single (date, tribunal) pair. Thread-safe.

    Returns:
        'success' or 'failed' for stats aggregation.
    """
    absent_marker = f"djen-{date_str}-{tribunal}.absent"

    logger.info("processing", date=date_str, tribunal=tribunal)

    # Get caderno info
    info = get_caderno_info(api_client, proxy_url, tribunal, date_str)

    if isinstance(info, AbsentReason):
        # Mark as absent to complete the day's matrix
        logger.info("no_caderno_found", date=date_str, tribunal=tribunal)
        item_id = f"djen-{date_str}"
        with tempfile.TemporaryDirectory() as tmpdir:
            marker_path = Path(tmpdir) / absent_marker
            marker_path.write_text(json.dumps(asdict(info), ensure_ascii=False) + "\n")
            ok = upload_to_ia(upload_client, item_id, marker_path, date_str)
            return "success" if ok else "failed"

    if not isinstance(info, dict):
        # API returned None — transient error after retries (5xx, timeout, network)
        logger.warning("caderno_api_transient_error", date=date_str, tribunal=tribunal)
        return "failed"

    download_url = info.get("url")
    if not download_url:
        return "failed"

    # Download and upload
    zip_name = f"djen-{date_str}-{tribunal}.zip"
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / zip_name

        if not download_zip(dl_client, download_url, zip_path):
            return "failed"

        # Upload to IA (one item per day)
        item_id = f"djen-{date_str}"
        if upload_to_ia(upload_client, item_id, zip_path, date_str):
            logger.info("uploaded", item_id=item_id, file=zip_name)
            return "success"
        return "failed"


def collect_data(  # noqa: PLR0913
    proxy_url: str,
    target_date: str | None = None,
    target_tribunal: str | None = None,
    max_items: int = 50,
    backfill_days: int = 7,
    workers: int = 8,
    backfill: bool = False,
) -> dict[str, int]:
    """Main collection function with parallel processing.

    When *backfill* is True and no target_date is given, the rolling window
    (backfill_days) is processed first. Any remaining capacity (up to
    max_items) is filled from the catalog's backfill-needed.parquet, ordered
    most-recent-first (d-1, d-2, d-3 …).
    """
    stats: dict[str, int] = {"success": 0, "failed": 0, "skipped": 0}

    # Build list of (date, tribunal) pairs to process FIRST,
    # so we know which dates to check on IA (targeted lookup).
    to_process: list[tuple[str, str]] = []

    # Fetch the current tribunal list from DJEN API, merged with fallback
    all_tribunais = fetch_tribunais_from_api(proxy_url)

    if target_date:
        # Specific date
        tribunais = [target_tribunal.upper()] if target_tribunal else all_tribunais
        for tribunal in tribunais:
            to_process.append((target_date, tribunal))
    else:
        # Backfill recent days
        today = date.today()
        for days_ago in range(1, backfill_days + 1):
            d = today - timedelta(days=days_ago)
            # Skip weekends (courts don't publish)
            if d.weekday() >= 5:
                continue
            date_str = d.strftime("%Y-%m-%d")
            for tribunal in all_tribunais:
                to_process.append((date_str, tribunal))

    # Check only the dates we actually need — O(backfill_days) requests
    # instead of scanning every djen-* item on IA (O(total_days_ever)).
    dates_to_check = sorted({d for d, _ in to_process})
    existing_files = get_existing_files_for_dates(dates_to_check)

    # Pre-filter already-existing items, then apply max_items limit
    pending: list[tuple[str, str]] = []
    for date_str, tribunal in to_process:
        zip_name = f"djen-{date_str}-{tribunal}.zip"
        absent_marker = f"djen-{date_str}-{tribunal}.absent"
        if zip_name in existing_files or absent_marker in existing_files:
            stats["skipped"] += 1
        else:
            pending.append((date_str, tribunal))

    # ── Backfill: append historical items from catalog ──────────────
    if backfill and not target_date and len(pending) < max_items:
        rolling_date_set = set(dates_to_check)
        remaining = max_items - len(pending)

        catalog_items = fetch_backfill_items()
        # Exclude dates already covered by the rolling window
        candidates = [
            (d, t) for d, t in catalog_items if d not in rolling_date_set
        ]
        # Take a buffer (3×) to survive items already collected since last catalog update
        candidates = candidates[: remaining * 3]

        if candidates:
            backfill_dates = sorted({d for d, _ in candidates})
            backfill_existing = get_existing_files_for_dates(backfill_dates)
            for d, t in candidates:
                zip_name = f"djen-{d}-{t}.zip"
                absent_marker = f"djen-{d}-{t}.absent"
                if zip_name in backfill_existing or absent_marker in backfill_existing:
                    stats["skipped"] += 1
                else:
                    pending.append((d, t))
                if len(pending) >= max_items:
                    break

            logger.info(
                "backfill_items_appended",
                catalog_candidates=len(candidates),
                pending_after=len(pending),
            )

    pending = pending[:max_items]

    logger.info(
        "items_to_process",
        total=len(to_process),
        pending=len(pending),
        skipped=stats["skipped"],
        max_items=max_items,
        workers=workers,
    )

    if not pending:
        return stats

    # Resolve IA S3 credentials once (shared via upload client headers)
    ia_auth = _get_ia_s3_auth()
    if not ia_auth:
        logger.error(
            "ia_credentials_not_found",
            hint="Set IAS3_ACCESS_KEY/IAS3_SECRET_KEY or run `ia configure`",
        )
        stats["failed"] = len(pending)
        return stats

    # Shared HTTP clients with connection pooling
    api_timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
    dl_timeout = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)
    upload_timeout = httpx.Timeout(connect=10.0, read=300.0, write=300.0, pool=10.0)
    pool_limits = httpx.Limits(
        max_connections=workers * 2,
        max_keepalive_connections=workers,
    )

    with (
        httpx.Client(timeout=api_timeout, limits=pool_limits) as api_client,
        httpx.Client(
            timeout=dl_timeout,
            limits=pool_limits,
            follow_redirects=True,
        ) as dl_client,
        httpx.Client(
            timeout=upload_timeout,
            limits=pool_limits,
            headers={"Authorization": ia_auth},
        ) as upload_client,
        ThreadPoolExecutor(max_workers=workers) as executor,
    ):
        futures = {
            executor.submit(
                _process_item,
                api_client,
                dl_client,
                upload_client,
                proxy_url,
                date_str,
                tribunal,
            ): (date_str, tribunal)
            for date_str, tribunal in pending
        }
        for future in as_completed(futures):
            try:
                result = future.result()
                stats[result] += 1
            except Exception:
                dt, trib = futures[future]
                logger.exception("worker_error", date=dt, tribunal=trib)
                stats["failed"] += 1

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect DJEN data")
    parser.add_argument("--proxy-url", default="https://djen-proxy-mhgmawcn3a-rj.a.run.app")
    parser.add_argument("--date", help="Specific date (YYYY-MM-DD)")
    parser.add_argument("--tribunal", help="Specific tribunal (e.g., TJSP)")
    parser.add_argument("--max-items", type=int, default=50)
    parser.add_argument("--backfill-days", type=int, default=7)
    parser.add_argument("--workers", type=int, default=8, help="Number of parallel workers")
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="After the rolling window, fill historical gaps from the catalog (d-1 first)",
    )
    args = parser.parse_args()

    print("Collecting DJEN data...")
    print(f"  Proxy: {args.proxy_url}")
    if args.date:
        print(f"  Date: {args.date}")
    if args.tribunal:
        print(f"  Tribunal: {args.tribunal}")
    print(f"  Max items: {args.max_items}")
    print(f"  Workers: {args.workers}")
    if args.backfill:
        print("  Backfill: ENABLED (catalog-driven, d-1 priority)")
    print()

    stats = collect_data(
        proxy_url=args.proxy_url,
        target_date=args.date,
        target_tribunal=args.tribunal,
        max_items=args.max_items,
        backfill_days=args.backfill_days,
        workers=args.workers,
        backfill=args.backfill,
    )

    print()
    print("=" * 40)
    print("COLLECTION SUMMARY")
    print("=" * 40)
    print(f"  Success: {stats['success']}")
    print(f"  Failed:  {stats['failed']}")
    print(f"  Skipped: {stats['skipped']} (already on IA)")

    # Determine exit code based on success rate, not strict zero-failures
    # This tolerates transient API errors (timeouts, 5xx, network issues)
    total_processed = stats["success"] + stats["failed"]
    if total_processed == 0:
        # Nothing to process is a success
        print("\n  Status: SUCCESS (nothing to process)")
        return 0

    success_rate = stats["success"] / total_processed
    failure_threshold = 0.2  # Fail only if >20% failure rate

    if stats["failed"] / total_processed <= failure_threshold:
        print(f"\n  Status: SUCCESS ({success_rate:.0%} success rate)")
        return 0
    print(f"\n  Status: FAILED ({success_rate:.0%} success rate, threshold: 80%)")
    return 1


if __name__ == "__main__":
    exit(main())
