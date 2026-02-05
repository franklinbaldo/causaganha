#!/usr/bin/env python3
"""Collect DJEN data and upload to Internet Archive.

This script downloads judicial communications from the DJEN API and uploads
them to Internet Archive for permanent archival.

Uses asyncio to avoid GIL issues on Windows with httpx socket operations.

Usage:
    # Collect recent data (default: last 7 days)
    python scripts/pipeline/collect.py

    # Collect specific date
    python scripts/pipeline/collect.py --date 2026-01-27

    # Collect specific tribunal
    python scripts/pipeline/collect.py --date 2026-01-27 --tribunal TJSP

    # Limit number of items
    python scripts/pipeline/collect.py --max-items 10
"""

import argparse
import asyncio
import configparser
import json
import os
import tempfile
import time
from concurrent.futures import CancelledError, ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
import duckdb
import httpx
import structlog
from botocore.config import Config
from botocore.exceptions import ClientError

from causaganha.config import TRIBUNAIS
from causaganha.utils import validate_url


BACKFILL_PARQUET_URL = "https://archive.org/download/causaganha-catalog/backfill-needed.parquet"
DJEN_CACHE_FILE = Path("djen_cache.json")
DB_PATH = Path("data/causaganha.duckdb")

SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS djen_state;
CREATE TABLE IF NOT EXISTS djen_state.coverage (
    date DATE NOT NULL,
    tribunal VARCHAR NOT NULL,
    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, tribunal)
);
"""


@dataclass
class AbsentReason:
    """Evidence for why a journal was marked absent."""

    status_code: int
    reason: str
    checked_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    response_snippet: str = ""


logger = structlog.get_logger()


def parse_deadline(duration_str: str) -> int:
    """Parse a deadline string (e.g. '10m', '600s') into seconds."""
    if not duration_str:
        return 0
    duration_str = duration_str.strip().lower()
    try:
        if duration_str.endswith("m"):
            return int(float(duration_str[:-1]) * 60)
        if duration_str.endswith("s"):
            return int(float(duration_str[:-1]))
        return int(float(duration_str))
    except ValueError:
        return 0


def get_db_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Get DuckDB connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH), read_only=read_only)


def init_db(con: duckdb.DuckDBPyConnection) -> None:
    """Initialize database schema."""
    con.execute(SCHEMA_SQL)


def migrate_legacy_cache(con: duckdb.DuckDBPyConnection) -> None:
    """Migrate JSON cache to DuckDB if it exists."""
    if not DJEN_CACHE_FILE.exists():
        return

    logger.info("migrating_cache", file=str(DJEN_CACHE_FILE))
    try:
        cache = json.loads(DJEN_CACHE_FILE.read_text())
        rows = []
        for date_str, files in cache.items():
            for filename in files:
                # Filename format: djen-{date}-{tribunal}.{ext}
                # e.g. djen-2024-01-01-TJSP.zip or djen-2024-01-01-TJSP.absent
                try:
                    parts = filename.split(".")
                    stem = parts[0]
                    # stem: djen-2024-01-01-TJSP
                    # Split by '-'
                    segments = stem.split("-")
                    if len(segments) >= 5:
                        tribunal = segments[-1]
                        # date is segments[1:4] joined by '-'
                        date_parsed = "-".join(segments[1:4])
                        # Verify date matches key
                        if date_parsed == date_str:
                            rows.append((date_str, tribunal))
                except Exception:
                    continue

        if rows:
            con.executemany(
                "INSERT INTO djen_state.coverage (date, tribunal) VALUES (?, ?) ON CONFLICT DO NOTHING",
                rows,
            )
            logger.info("migrated_rows", count=len(rows))

        DJEN_CACHE_FILE.unlink()
        logger.info("cache_migration_complete")

    except Exception as e:
        logger.warning("migration_failed", error=str(e))


def get_coverage_for_dates(
    con: duckdb.DuckDBPyConnection, dates: list[str]
) -> set[tuple[str, str]]:
    """Get set of (date, tribunal) present in DB for given dates."""
    if not dates:
        return set()

    # We query for all records matching the dates.
    # Dynamically build placeholders
    placeholders = ",".join(["?"] * len(dates))
    query = f"SELECT CAST(date AS VARCHAR), tribunal FROM djen_state.coverage WHERE date IN ({placeholders})"

    result = con.execute(query, dates).fetchall()
    return {(r[0], r[1]) for r in result}


def mark_downloaded(con: duckdb.DuckDBPyConnection, items: list[tuple[str, str]]) -> None:
    """Mark (date, tribunal) as covered."""
    if not items:
        return
    con.executemany(
        "INSERT INTO djen_state.coverage (date, tribunal) VALUES (?, ?) ON CONFLICT DO NOTHING",
        items,
    )


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


async def _fetch_ia_files_for_date_async(client: httpx.AsyncClient, date_str: str) -> list[str]:
    """Fetch zip/absent filenames for a single date from IA metadata API (async).

    Uses the lightweight HTTP metadata endpoint (one request per date)
    instead of the heavy internetarchive library search which scans
    ALL items on every invocation.
    """
    item_id = f"djen-{date_str}"
    url = f"https://archive.org/metadata/{item_id}"
    try:
        resp = await client.get(url, timeout=30)
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


async def get_existing_files_for_dates_async(dates: list[str]) -> set[tuple[str, str]]:
    """Get existing (date, tribunal) pairs on IA for specific dates only (async).

    Queries the IA metadata HTTP API once per date, using asyncio for
    concurrent requests. The rolling window (d-1) produces ~1 request;
    backfill batches add a bounded extra set.

    Uses asyncio instead of threading to avoid GIL issues on Windows.
    """
    if not dates:
        return set()

    con = get_db_connection()
    init_db(con)
    migrate_legacy_cache(con)

    # Check DB coverage first
    # We get all known (date, tribunal) pairs for these dates
    known_coverage = get_coverage_for_dates(con, dates)

    # Identify which dates have NO coverage (or we want to re-check?)
    # Since we can't distinguish "checked and found nothing" from "never checked",
    # we might need to check IA for dates that have no entries in DB.
    # However, to be robust, we check IA for dates where we found nothing in DB.
    # If a date has at least one tribunal covered, we assume we checked it?
    # No, that's risky. But 'djen_cache.json' logic was: if key exists (even empty), don't check.
    # Here, we don't have "key exists".
    # So we calculate dates that have at least one entry.
    dates_with_coverage = {d for d, _ in known_coverage}
    dates_to_fetch = [d for d in dates if d not in dates_with_coverage]

    if not dates_to_fetch:
        con.close()
        return known_coverage

    logger.info("checking_existing_files", dates_count=len(dates_to_fetch))

    async with httpx.AsyncClient() as client:
        tasks = [_fetch_ia_files_for_date_async(client, d) for d in dates_to_fetch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    fetched_coverage: set[tuple[str, str]] = set()
    new_coverage: list[tuple[str, str]] = []

    for i, result in enumerate(results):
        date_str = dates_to_fetch[i]
        if isinstance(result, list):
            # result is list of filenames
            for filename in result:
                # Parse tribunal from filename
                try:
                    parts = filename.split(".")
                    stem = parts[0]
                    segments = stem.split("-")
                    if len(segments) >= 5:
                        tribunal = segments[-1]
                        pair = (date_str, tribunal)
                        fetched_coverage.add(pair)
                        new_coverage.append(pair)
                except Exception:
                    pass
        else:
            # On error, ignore
            pass

    if new_coverage:
        mark_downloaded(con, new_coverage)

    con.close()

    total_coverage = known_coverage | fetched_coverage

    logger.info(
        "existing_files_found",
        count=len(total_coverage),
        dates_checked=len(dates_to_fetch),
    )
    return total_coverage


def get_existing_files_for_dates(dates: list[str]) -> set[tuple[str, str]]:
    """Sync wrapper for get_existing_files_for_dates_async."""
    # Re-enabled since we have caching and run on Linux
    return asyncio.run(get_existing_files_for_dates_async(dates))


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
    client: httpx.Client,
    url: str,
    output_path: Path,
    max_retries: int = 2,
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


def _get_ia_credentials() -> tuple[str, str] | None:
    """Get IA S3 access key and secret key from env vars or config file."""
    access = os.environ.get("IAS3_ACCESS_KEY", "")
    secret = os.environ.get("IAS3_SECRET_KEY", "")
    if access and secret:
        return access, secret
    # Fall back to config file (created by CI workflow)
    config_path = Path.home() / ".config" / "internetarchive" / "ia.ini"
    if config_path.exists():
        cfg = configparser.ConfigParser()
        cfg.read(config_path)
        access = cfg.get("s3", "access", fallback="")
        secret = cfg.get("s3", "secret", fallback="")
        if access and secret:
            return access, secret
    return None


def upload_to_ia(
    item_id: str,
    file_path: Path,
    date_str: str,
) -> bool:
    """Upload file to Internet Archive via the S3-compatible API.

    Uses boto3 with adaptive retries and MD5 integrity verification.
    """
    creds = _get_ia_credentials()
    if not creds:
        logger.error(
            "ia_credentials_not_found",
            hint="Set IAS3_ACCESS_KEY/IAS3_SECRET_KEY or run `ia configure`",
        )
        return False
    access_key, secret_key = creds

    retry_config = Config(retries={"max_attempts": 10, "mode": "adaptive"})

    try:
        s3 = boto3.client(
            "s3",
            endpoint_url="https://s3.us.archive.org",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=retry_config,
        )

        # Register event to add custom headers for IA-specific flags
        def add_custom_headers(params, **kwargs):
            if "headers" not in params:
                params["headers"] = {}
            params["headers"]["x-archive-auto-make-bucket"] = "1"
            params["headers"]["x-archive-queue-derive"] = "0"

        s3.meta.events.register("before-call:s3:PutObject", add_custom_headers)

        with file_path.open("rb") as f:
            s3.put_object(
                Bucket=item_id,
                Key=file_path.name,
                Body=f,
                Metadata={
                    "collection": "opensource",
                    "mediatype": "data",
                    "title": f"DJEN Data - {date_str}",
                    "description": (
                        "Diario de Justica Eletronico Nacional - Judicial communications from Brazilian courts."
                    ),
                    "subject": "brazilian-law;djen;legal;judiciary;open-data",
                    "creator": "CausaGanha",
                    "date": date_str,
                },
            )
        return True

    except ClientError as e:
        logger.error("upload_failed", item_id=item_id, error=str(e))
        return False
    except Exception as e:
        logger.error("upload_unexpected_error", item_id=item_id, error=str(e))
        return False


def _process_item(
    api_client: httpx.Client,
    dl_client: httpx.Client,
    proxy_url: str,
    date_str: str,
    tribunal: str,
) -> tuple[str, float]:
    """Process a single (date, tribunal) pair. Thread-safe.

    Returns:
        ('success'|'failed', size_mb)
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
            ok = upload_to_ia(item_id, marker_path, date_str)
            return ("success", 0.0) if ok else ("failed", 0.0)

    if not isinstance(info, dict):
        # API returned None — transient error after retries (5xx, timeout, network)
        logger.warning("caderno_api_transient_error", date=date_str, tribunal=tribunal)
        return "failed", 0.0

    download_url = info.get("url")
    if not download_url:
        return "failed", 0.0

    # Download and upload
    zip_name = f"djen-{date_str}-{tribunal}.zip"
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / zip_name

        if not download_zip(dl_client, download_url, zip_path):
            return "failed", 0.0

        size_mb = zip_path.stat().st_size / (1024 * 1024)

        # Upload to IA (one item per day)
        item_id = f"djen-{date_str}"
        if upload_to_ia(item_id, zip_path, date_str):
            logger.info("uploaded", item_id=item_id, file=zip_name, size_mb=f"{size_mb:.2f}")
            return "success", size_mb
        return "failed", 0.0


def collect_data(
    proxy_url: str,
    target_date: str | None = None,
    target_tribunal: str | None = None,
    max_items: int = 50,
    workers: int = 8,
    deadline_seconds: int = 0,
) -> dict[str, int | float]:
    """Main collection function with parallel processing.

    When no target_date is given, the work queue comes straight from the
    catalog's backfill-needed.parquet — every (date, tribunal) pair not
    yet on Internet Archive, ordered most-recent-first (d-1, d-2, d-3 …).
    The catalog is the single source of truth; we only verify against IA
    to filter items collected since the last catalog rebuild (daily 06:00 UTC).
    """
    stats: dict[str, int | float] = {"success": 0, "failed": 0, "skipped": 0, "downloaded_mb": 0.0}

    all_tribunais = fetch_tribunais_from_api(proxy_url)

    if target_date:
        # Manual: specific date (+ optional tribunal filter)
        tribunais = [target_tribunal.upper()] if target_tribunal else all_tribunais
        to_process = [(target_date, t) for t in tribunais]
    else:
        # Autonomous: catalog tells us what's missing, d-1 first
        to_process = fetch_backfill_items()

    # Scan backfill queue in chunks to find items needing collection
    # Process 2000 items per IA check batch to handle stale catalog
    pending: list[tuple[str, str]] = []
    chunk_size = max_items * 10  # 2000 items per batch

    for chunk_start in range(0, len(to_process), chunk_size):
        chunk = to_process[chunk_start : chunk_start + chunk_size]
        dates_to_check = sorted({d for d, _ in chunk})
        existing_coverage = get_existing_files_for_dates(dates_to_check)

        for d, t in chunk:
            if (d, t) in existing_coverage:
                stats["skipped"] += 1
            else:
                pending.append((d, t))
                if len(pending) >= max_items:
                    break

        if len(pending) >= max_items:
            break

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

    # Verify IA credentials exist before starting
    if not _get_ia_credentials():
        logger.error(
            "ia_credentials_not_found",
            hint="Set IAS3_ACCESS_KEY/IAS3_SECRET_KEY or run `ia configure`",
        )
        stats["failed"] = len(pending)
        return stats

    # Shared HTTP clients with connection pooling
    api_timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
    dl_timeout = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)
    pool_limits = httpx.Limits(
        max_connections=workers * 2,
        max_keepalive_connections=workers,
    )

    start_time = time.time()

    with (
        httpx.Client(timeout=api_timeout, limits=pool_limits) as api_client,
        httpx.Client(
            timeout=dl_timeout,
            limits=pool_limits,
            follow_redirects=True,
        ) as dl_client,
        ThreadPoolExecutor(max_workers=workers) as executor,
    ):
        futures = {
            executor.submit(_process_item, api_client, dl_client, proxy_url, date_str, tribunal): (
                date_str,
                tribunal,
            )
            for date_str, tribunal in pending
        }

        # Open DB connection for marking downloads
        con = get_db_connection()
        init_db(con)

        try:
            for future in as_completed(futures):
                # Check deadline
                if deadline_seconds > 0:
                    elapsed = time.time() - start_time
                    if elapsed > deadline_seconds:
                        logger.warning(
                            "deadline_reached",
                            elapsed=f"{elapsed:.1f}s",
                            limit=f"{deadline_seconds}s",
                            pending=len(futures) - (stats["success"] + stats["failed"]),
                        )
                        # Cancel remaining
                        for f in futures:
                            f.cancel()
                        break

                date_str, tribunal = futures[future]
                try:
                    result, size_mb = future.result()
                    stats[result] += 1
                    stats["downloaded_mb"] += size_mb

                    # NEW: Mark successful downloads immediately
                    if result == "success":
                        mark_downloaded(con, [(date_str, tribunal)])

                except CancelledError:
                    pass
                except Exception:
                    logger.exception("worker_error", date=date_str, tribunal=tribunal)
                    stats["failed"] += 1
        finally:
            con.close()

    return stats


def calculate_exit_code(stats: dict[str, int | float]) -> int:
    """Determine exit code based on collection statistics.

    Policy:
      - If nothing to process: SUCCESS (0)
      - If success rate >= 5%: SUCCESS (0)
      - If success rate < 5%: FAILED (1)
    """
    total_processed = stats["success"] + stats["failed"]

    if total_processed == 0:
        print("\n  Status: SUCCESS (nothing to process)")
        return 0

    success_rate = stats["success"] / total_processed
    min_threshold = 0.05  # 5%

    if success_rate >= min_threshold:
        print(f"\n  Status: SUCCESS ({success_rate:.1%} success rate)")
        return 0

    print(f"\n  Status: FAILED ({success_rate:.1%} success rate, min: {min_threshold:.0%})")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect DJEN data")
    parser.add_argument("--proxy-url", default="https://djen-proxy-mhgmawcn3a-rj.a.run.app")
    parser.add_argument("--date", help="Specific date (YYYY-MM-DD)")
    parser.add_argument("--tribunal", help="Specific tribunal (e.g., TJSP)")
    parser.add_argument("--max-items", type=int, default=50)
    parser.add_argument("--workers", type=int, default=8, help="Number of parallel workers")
    parser.add_argument(
        "--deadline",
        help="Exit after this duration (e.g., 10m, 600s)",
        default="10m",
    )
    args = parser.parse_args()

    # Validate security inputs
    if args.proxy_url is not None:
        try:
            validate_url(args.proxy_url)
        except ValueError as e:
            print(f"❌ Security Error: {e}")
            return 1

    print("Collecting DJEN data...")
    print(f"  Proxy: {args.proxy_url}")
    if args.date:
        print(f"  Date: {args.date}")
    else:
        print("  Source: catalog (backfill-needed.parquet, d-1 first)")
    if args.tribunal:
        print(f"  Tribunal: {args.tribunal}")
    deadline_sec = parse_deadline(args.deadline)
    print(f"  Max items: {args.max_items}")
    print(f"  Workers: {args.workers}")
    print(f"  Deadline: {args.deadline} ({deadline_sec}s)")
    print()

    stats = collect_data(
        proxy_url=args.proxy_url,
        target_date=args.date,
        target_tribunal=args.tribunal,
        max_items=args.max_items,
        workers=args.workers,
        deadline_seconds=deadline_sec,
    )

    print()
    print("=" * 40)
    print("COLLECTION SUMMARY")
    print("=" * 40)
    print(f"  Success: {stats['success']}")
    print(f"  Failed:  {stats['failed']}")
    print(f"  Skipped: {stats['skipped']} (already on IA)")
    print(f"  Downloaded: {stats['downloaded_mb']:.1f} MB")

    # Set GitHub Actions output: did we add any files?
    files_added = stats["success"] > 0
    print(f"\n  Files added: {files_added}")

    # Output for GitHub Actions conditional triggers
    if os_env := os.getenv("GITHUB_OUTPUT"):
        with open(os_env, "a") as f:
            f.write(f"files_added={'true' if files_added else 'false'}\n")
            f.write(f"collect_success={stats['success']}\n")
            f.write(f"collect_failed={stats['failed']}\n")
            f.write(f"collect_skipped={stats['skipped']}\n")
            f.write(f"collect_downloaded_mb={stats['downloaded_mb']:.1f}\n")

    return calculate_exit_code(stats)


if __name__ == "__main__":
    exit(main())
