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

    # Control parallelism (default: 6 workers)
    python scripts/pipeline/collect.py --workers 8
"""

import argparse
import json
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog


@dataclass
class AbsentReason:
    """Evidence for why a journal was marked absent."""

    status_code: int
    reason: str
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    response_snippet: str = ""


logger = structlog.get_logger()

# All 91 Brazilian courts
TRIBUNAIS = [
    # Federal Regional (6)
    "TRF1",
    "TRF2",
    "TRF3",
    "TRF4",
    "TRF5",
    "TRF6",
    # Superior (8)
    "STF",
    "STJ",
    "TST",
    "TSE",
    "STM",
    "CNJ",
    "CNMP",
    "TNU",
    # State (27)
    "TJAC",
    "TJAL",
    "TJAM",
    "TJAP",
    "TJBA",
    "TJCE",
    "TJDF",
    "TJES",
    "TJGO",
    "TJMA",
    "TJMG",
    "TJMS",
    "TJMT",
    "TJPA",
    "TJPB",
    "TJPE",
    "TJPI",
    "TJPR",
    "TJRJ",
    "TJRN",
    "TJRO",
    "TJRR",
    "TJRS",
    "TJSC",
    "TJSE",
    "TJSP",
    "TJTO",
    # Labor (24)
    "TRT1",
    "TRT2",
    "TRT3",
    "TRT4",
    "TRT5",
    "TRT6",
    "TRT7",
    "TRT8",
    "TRT9",
    "TRT10",
    "TRT11",
    "TRT12",
    "TRT13",
    "TRT14",
    "TRT15",
    "TRT16",
    "TRT17",
    "TRT18",
    "TRT19",
    "TRT20",
    "TRT21",
    "TRT22",
    "TRT23",
    "TRT24",
    # Electoral (27)
    "TREAC",
    "TREAL",
    "TREAM",
    "TREAP",
    "TREBA",
    "TRECE",
    "TREDF",
    "TREES",
    "TREGO",
    "TREMA",
    "TREMG",
    "TREMS",
    "TREMT",
    "TREPA",
    "TREPB",
    "TREPE",
    "TREPI",
    "TREPR",
    "TRERJ",
    "TRERN",
    "TRERO",
    "TRERR",
    "TRERS",
    "TRESC",
    "TRESE",
    "TRESP",
    "TRETO",
]


def _list_item_files(item_id: str) -> list[str]:
    """List zip/absent files for a single IA item. Thread-safe."""
    try:
        result = subprocess.run(
            ["ia", "list", item_id, "--glob", "*.{zip,absent}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except subprocess.TimeoutExpired:
        pass
    return []


def get_existing_files_on_ia(workers: int = 8) -> set[str]:
    """Get list of ZIP/absent files already on Internet Archive.

    Uses parallel queries to speed up metadata fetching.
    """
    logger.info("fetching_existing_files")
    existing: set[str] = set()

    try:
        # List all djen-* items
        result = subprocess.run(
            ["ia", "search", "identifier:djen-20*", "--itemlist"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            logger.warning("ia_search_failed", stderr=result.stderr[:200])
            return existing

        items = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        logger.info("ia_items_found", count=len(items))

        # Query file listings in parallel instead of sequentially
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_list_item_files, item_id): item_id for item_id in items
            }
            for future in as_completed(futures):
                for filename in future.result():
                    existing.add(filename)

    except subprocess.TimeoutExpired:
        logger.warning("ia_search_timeout")
    except FileNotFoundError:
        logger.error("ia_cli_not_found")

    logger.info("existing_files_found", count=len(existing))
    return existing


def get_caderno_info(
    client: httpx.Client, proxy_url: str, tribunal: str, date_str: str,
) -> dict[str, Any] | AbsentReason | None:
    """Get caderno (journal) info from DJEN API.

    Args:
        client: Shared httpx client for connection pooling.
        proxy_url: Base URL of the DJEN proxy.
        tribunal: Court identifier (e.g. TJSP).
        date_str: Date in YYYY-MM-DD format.

    Returns:
        dict: Success (journal data)
        AbsentReason: No journal for this day (with evidence)
        None: Transient error (timeout, 5xx, etc.)
    """
    url = f"{proxy_url}/api/v1/caderno/{tribunal}/{date_str}/D"

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
        logger.warning(
            "caderno_api_error",
            tribunal=tribunal,
            date=date_str,
            status=response.status_code,
        )
        return None
    except Exception as e:
        logger.debug("caderno_fetch_failed", tribunal=tribunal, date=date_str, error=str(e))
        return None


def download_zip(client: httpx.Client, url: str, output_path: Path) -> bool:
    """Download ZIP file from DJEN using streaming to reduce memory usage.

    Args:
        client: Shared httpx client for connection pooling.
        url: Download URL for the ZIP file.
        output_path: Local path to write the downloaded file.
    """
    try:
        with client.stream("GET", url) as response:
            if response.status_code != 200:
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
        logger.warning("download_failed", url=url[:100], error=str(e))
        if output_path.exists():
            output_path.unlink()
        return False


def upload_to_ia(item_id: str, file_path: Path, date_str: str) -> bool:
    """Upload file to Internet Archive."""
    try:
        result = subprocess.run(
            [
                "ia",
                "upload",
                item_id,
                str(file_path),
                "--metadata=collection:opensource",
                "--metadata=mediatype:data",
                f"--metadata=title:DJEN Data - {date_str}",
                "--metadata=description:Diario de Justica Eletronico Nacional - Judicial communications from Brazilian courts.",
                "--metadata=subject:brazilian-law;djen;legal;judiciary;open-data",
                "--metadata=creator:CausaGanha",
                f"--metadata=date:{date_str}",
                "--retries=3",
                "--no-derive",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.warning("upload_timeout", item_id=item_id)
        return False
    except Exception as e:
        logger.warning("upload_failed", item_id=item_id, error=str(e))
        return False


def _process_item(
    api_client: httpx.Client,
    dl_client: httpx.Client,
    proxy_url: str,
    date_str: str,
    tribunal: str,
) -> str:
    """Process a single (date, tribunal) pair. Thread-safe.

    Returns:
        'success' or 'failed' for stats aggregation.
    """
    zip_name = f"djen-{date_str}-{tribunal}.zip"
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
            return "success" if upload_to_ia(item_id, marker_path, date_str) else "failed"

    if not isinstance(info, dict):
        # API returned None - transient error (timeout, 4xx/5xx, network issue)
        logger.warning("caderno_api_transient_error", date=date_str, tribunal=tribunal)
        return "failed"

    download_url = info.get("url")
    if not download_url:
        return "failed"

    # Download and upload
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / zip_name

        if not download_zip(dl_client, download_url, zip_path):
            return "failed"

        # Upload to IA (one item per day)
        item_id = f"djen-{date_str}"
        if upload_to_ia(item_id, zip_path, date_str):
            logger.info("uploaded", item_id=item_id, file=zip_name)
            return "success"
        return "failed"


def collect_data(  # noqa: PLR0913
    proxy_url: str,
    target_date: str | None = None,
    target_tribunal: str | None = None,
    max_items: int = 50,
    backfill_days: int = 7,
    workers: int = 6,
) -> dict[str, int]:
    """Main collection function with parallel processing."""
    stats: dict[str, int] = {"success": 0, "failed": 0, "skipped": 0}

    # Get existing files to avoid duplicates (parallel metadata queries)
    existing_files = get_existing_files_on_ia(workers=workers)

    # Build list of (date, tribunal) pairs to process
    to_process: list[tuple[str, str]] = []

    if target_date:
        # Specific date
        tribunais = [target_tribunal.upper()] if target_tribunal else TRIBUNAIS
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
            for tribunal in TRIBUNAIS:
                to_process.append((date_str, tribunal))

    # Pre-filter already-existing items, then apply max_items limit
    pending: list[tuple[str, str]] = []
    for date_str, tribunal in to_process:
        zip_name = f"djen-{date_str}-{tribunal}.zip"
        absent_marker = f"djen-{date_str}-{tribunal}.absent"
        if zip_name in existing_files or absent_marker in existing_files:
            stats["skipped"] += 1
        else:
            pending.append((date_str, tribunal))

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

    # Shared HTTP clients with connection pooling
    api_timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
    dl_timeout = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)
    pool_limits = httpx.Limits(
        max_connections=workers * 2,
        max_keepalive_connections=workers,
    )

    with (
        httpx.Client(timeout=api_timeout, limits=pool_limits) as api_client,
        httpx.Client(
            timeout=dl_timeout, limits=pool_limits, follow_redirects=True,
        ) as dl_client,
        ThreadPoolExecutor(max_workers=workers) as executor,
    ):
        futures = {
            executor.submit(
                _process_item, api_client, dl_client, proxy_url, date_str, tribunal,
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
    parser.add_argument("--workers", type=int, default=6, help="Number of parallel workers")
    args = parser.parse_args()

    print("Collecting DJEN data...")
    print(f"  Proxy: {args.proxy_url}")
    if args.date:
        print(f"  Date: {args.date}")
    if args.tribunal:
        print(f"  Tribunal: {args.tribunal}")
    print(f"  Max items: {args.max_items}")
    print(f"  Workers: {args.workers}")
    print()

    stats = collect_data(
        proxy_url=args.proxy_url,
        target_date=args.date,
        target_tribunal=args.tribunal,
        max_items=args.max_items,
        backfill_days=args.backfill_days,
        workers=args.workers,
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
    else:
        print(f"\n  Status: FAILED ({success_rate:.0%} success rate, threshold: 80%)")
        return 1


if __name__ == "__main__":
    exit(main())
