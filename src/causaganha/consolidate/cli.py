"""Typer-based CLI for the consolidation pipeline.

Usage::

    # Consolidate a single date
    python -m causaganha.consolidate date 2026-04-13

    # Consolidate an entire (tribunal, year)
    python -m causaganha.consolidate tribunal-year TJSP 2026

    # Backfill: auto-find unconsolidated dates and process until deadline
    python -m causaganha.consolidate backfill --deadline 30m --max-dates 5

Memory-bounded by design: all queries are pushed to DuckDB; ZIP contents
stream to NDJSON rather than materialize in Python.
"""

from __future__ import annotations

import asyncio
import tempfile
import time
from pathlib import Path
from typing import Annotated

import ibis
import structlog
import typer

from causaganha.consolidate import checkpoint, manifest_reader
from causaganha.consolidate.exporter import export_and_upload_table, upload_marker
from causaganha.consolidate.transforms import TABLES, init_tables, load_and_transform
from causaganha.consolidate.zip_processor import process_zip_entry
from causaganha.pipeline.ia_s3 import (
    CircuitBreaker,
    create_upload_client,
    get_ia_s3_auth,
)


log = structlog.get_logger()

app = typer.Typer(
    help="DJEN ZIP → Parquet consolidation pipeline",
    no_args_is_help=True,
)


def _get_connection(db_path: Path | None = None, memory_limit: str = "2GB") -> ibis.BaseBackend:
    """Create a DuckDB connection via ibis.

    Passes a file path to keep pages on disk (spills when RAM fills),
    avoiding OOM on large tribunal-year consolidations. Caps DuckDB's
    internal memory budget too so it starts spilling early.
    """
    con = ibis.duckdb.connect(":memory:" if db_path is None else str(db_path))
    # Apply memory cap — DuckDB will spill to disk when exceeded
    con.raw_sql(f"SET memory_limit='{memory_limit}'")
    return con


async def _consolidate_zips(
    zips: list[dict],
    item_id: str,
    date_tag: str,
    *,
    dry_run: bool,
    workers: int,
    local_zips: str | None = None,
) -> dict[str, int | float]:
    """Shared consolidation body: download ZIPs → NDJSON → Parquet → IA upload."""
    stats: dict[str, int | float] = {
        "zips_processed": 0,
        "records": 0,
        "parquets_created": 0,
        "uploaded": 0,
        "uploaded_mb": 0.0,
    }

    if not zips:
        log.info("nothing_to_consolidate", item_id=item_id)
        return stats

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        ndjson_dir = tmp_path / "ndjson"
        ndjson_dir.mkdir()

        # Persistent DuckDB file so large tables spill to disk instead of RAM
        db_path = tmp_path / "consolidate.duckdb"
        con = _get_connection(db_path)
        init_tables(con)

        # Download + extract in parallel — bounded by workers
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    process_zip_entry,
                    zip_entry,
                    tmp_path,
                    ndjson_dir,
                    item_id,
                    local_zips=local_zips,
                ): zip_entry
                for zip_entry in zips
            }
            for future in as_completed(futures):
                zip_entry = futures[future]
                try:
                    success_cnt, records_cnt = future.result()
                    stats["zips_processed"] += success_cnt
                    stats["records"] += records_cnt
                except (OSError, ValueError) as e:
                    log.exception(
                        "zip_processing_error",
                        zip=zip_entry.get("filename"),
                        error=str(e),
                    )

        if stats["records"] == 0:
            log.warning("no_records_extracted", item_id=item_id)
            return stats

        # Transform NDJSON → 10 DuckDB tables via Ibis
        table_counts = load_and_transform(con, ndjson_dir, item_id)
        log.info("transform_complete", item_id=item_id, tables=table_counts)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        ia_auth = get_ia_s3_auth() or ""
        if not ia_auth and not dry_run:
            log.warning(
                "ia_credentials_not_found",
                hint="Set IAS3_ACCESS_KEY/IAS3_SECRET_KEY",
            )
            return stats

        breaker = CircuitBreaker(threshold=5)

        async with create_upload_client(ia_auth) as client:
            results = await asyncio.gather(
                *[
                    export_and_upload_table(
                        table_name,
                        con,
                        output_dir,
                        item_id,
                        client,
                        date_tag,
                        dry_run=dry_run,
                        circuit_breaker=breaker,
                    )
                    for table_name in TABLES
                ],
                return_exceptions=True,
            )
            for table_name, result in zip(TABLES, results, strict=True):
                if isinstance(result, Exception):
                    log.exception(
                        "table_export_error",
                        table=table_name,
                        error=str(result),
                    )
                    continue
                success, size_mb, uploaded = result
                if success:
                    stats["parquets_created"] += 1
                    stats["uploaded"] += uploaded
                    stats["uploaded_mb"] += size_mb

            if stats["parquets_created"] > 0 and not dry_run and await upload_marker(
                client, item_id, date_tag, circuit_breaker=breaker
            ):
                log.info("marker_uploaded", item_id=item_id)

    return stats


def _print_stats(stats: dict) -> None:
    log.info(
        "consolidation_stats",
        zips=stats.get("zips_processed"),
        records=stats.get("records"),
        parquets=stats.get("parquets_created"),
        uploaded=stats.get("uploaded"),
        mb=f"{stats.get('uploaded_mb', 0):.1f}",
    )


@app.command()
def date(
    target_date: Annotated[str, typer.Argument(help="Date to consolidate (YYYY-MM-DD)")],
    *,
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip IA uploads"),
    workers: int = typer.Option(4, "--workers", help="Parallel ZIP processors"),
) -> None:
    """Consolidate all ZIPs for a single date into a per-date IA item."""
    zips = manifest_reader.uploaded_zips_for_date(target_date)
    item_id = f"djen-{target_date}"
    stats = asyncio.run(
        _consolidate_zips(zips, item_id, target_date, dry_run=dry_run, workers=workers)
    )
    _print_stats(stats)
    if not dry_run and stats["parquets_created"] > 0:
        checkpoint.mark_date_complete(target_date)


@app.command("tribunal-year")
def tribunal_year(
    tribunal: Annotated[str, typer.Argument(help="Tribunal code (e.g. TJSP)")],
    year: Annotated[int, typer.Argument(help="Year (e.g. 2026)")],
    *,
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip IA uploads"),
    workers: int = typer.Option(4, "--workers", help="Parallel ZIP processors"),
) -> None:
    """Consolidate all ZIPs for a (tribunal, year) into a per-tribunal-year IA item."""
    zips = manifest_reader.uploaded_zips_for_tribunal_year(tribunal, year)
    item_id = f"djen-{tribunal.lower()}-{year}"
    date_tag = f"{year}-01-01"
    stats = asyncio.run(
        _consolidate_zips(zips, item_id, date_tag, dry_run=dry_run, workers=workers)
    )
    _print_stats(stats)


@app.command()
def backfill(
    *,
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip IA uploads"),
    workers: int = typer.Option(4, "--workers", help="Parallel ZIP processors per date"),
    max_dates: int = typer.Option(0, "--max-dates", help="Max dates per run (0 = all)"),
    deadline_seconds: int = typer.Option(600, "--deadline-seconds", help="Stop after N seconds"),
) -> None:
    """Find unconsolidated dates (newest first) and consolidate them until deadline."""
    from causaganha.consolidate.candidates import dates_needing_consolidation_from_ia

    start = time.monotonic()
    dates = dates_needing_consolidation_from_ia()
    log.info("backfill_candidates", count=len(dates))

    total_stats: dict[str, int | float] = {
        "zips_processed": 0,
        "records": 0,
        "parquets_created": 0,
        "uploaded": 0,
        "uploaded_mb": 0.0,
    }
    processed = 0

    for target_date in dates:
        if max_dates and processed >= max_dates:
            log.info("backfill_max_dates_reached", processed=processed)
            break
        if time.monotonic() - start > deadline_seconds:
            log.info("backfill_deadline_reached", elapsed=time.monotonic() - start)
            break
        if checkpoint.is_date_completed(target_date):
            log.info("backfill_already_done", date=target_date)
            continue

        zips = manifest_reader.uploaded_zips_for_date(target_date)
        item_id = f"djen-{target_date}"
        stats = asyncio.run(
            _consolidate_zips(
                zips, item_id, target_date, dry_run=dry_run, workers=workers
            )
        )
        for k in total_stats:
            total_stats[k] += stats.get(k, 0)

        if not dry_run and stats["parquets_created"] > 0:
            checkpoint.mark_date_complete(target_date)
        processed += 1

    _print_stats(total_stats)


if __name__ == "__main__":
    app()
