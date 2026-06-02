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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Annotated

import ibis
import structlog
import typer

from causaganha.consolidate import checkpoint, manifest_reader
from causaganha.consolidate.candidates import dates_needing_consolidation_from_ia
from causaganha.consolidate.consolidation_manifest import (
    collect_table_stats,
    update_consolidation_manifest,
)
from causaganha.consolidate.exporter import export_and_upload_table, upload_marker
from causaganha.consolidate.ndjson_validator import validate_ndjson_sample
from causaganha.consolidate.schema_registry import CURRENT_VERSION
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


def _process_zip_entries(
    zips: list[dict],
    tmp_path: Path,
    ndjson_dir: Path,
    item_id: str,
    *,
    workers: int,
    local_zips: str | None,
    stats: dict[str, int | float],
) -> None:
    """Download and extract ZIP entries into NDJSON, updating aggregate stats."""
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


def _collect_export_results(
    results: list[tuple[bool, float, int] | Exception],
    non_empty_tables: set[str],
    stats: dict[str, int | float],
) -> list[str]:
    """Fold per-table export results into stats. Returns list of uploaded table names."""
    uploaded_tables: list[str] = []
    for table_name, result in zip(TABLES, results, strict=True):
        if isinstance(result, Exception):
            log.error("table_export_error", table=table_name, error=str(result))
            if table_name in non_empty_tables:
                stats["export_failures"] += 1
            continue

        success, size_mb, uploaded = result
        if success:
            stats["parquets_created"] += 1
            stats["uploaded"] += uploaded
            stats["uploaded_mb"] += size_mb
            if uploaded:
                uploaded_tables.append(table_name)
        elif table_name in non_empty_tables:
            stats["export_failures"] += 1
    return uploaded_tables


def _exports_complete(
    non_empty_tables: set[str],
    stats: dict[str, int | float],
    item_id: str,
) -> bool:
    """Return true only when every non-empty table produced a valid Parquet."""
    expected_parquets = len(non_empty_tables)
    if stats["parquets_created"] == expected_parquets and stats["export_failures"] == 0:
        return True

    log.error(
        "marker_blocked_by_incomplete_exports",
        item_id=item_id,
        expected_parquets=expected_parquets,
        parquets_created=stats["parquets_created"],
        export_failures=stats["export_failures"],
    )
    return False


async def _export_upload_and_manifest(
    con: ibis.BaseBackend,
    output_dir: Path,
    item_id: str,
    date_tag: str,
    non_empty_tables: set[str],
    stats: dict[str, int | float],
    *,
    dry_run: bool,
) -> None:
    """Export all tables, validate, upload, write marker, and update manifest."""
    ia_auth = get_ia_s3_auth() or ""
    if not ia_auth and not dry_run:
        log.warning("ia_credentials_not_found", hint="Set IAS3_ACCESS_KEY/IAS3_SECRET_KEY")
        return

    breaker = CircuitBreaker(threshold=5)

    async with create_upload_client(ia_auth) as client:
        results = []
        for table_name in TABLES:
            try:
                res = await export_and_upload_table(
                    table_name,
                    con,
                    output_dir,
                    item_id,
                    client,
                    date_tag,
                    dry_run=dry_run,
                    circuit_breaker=breaker,
                )
                results.append(res)
            except Exception as exc:  # noqa: BLE001 — per-table resilience
                results.append(exc)
        uploaded_tables = _collect_export_results(results, non_empty_tables, stats)

        if _exports_complete(non_empty_tables, stats, item_id) and (
            stats["parquets_created"] > 0
            and not dry_run
            and await upload_marker(client, item_id, date_tag, circuit_breaker=breaker)
        ):
            stats["marker_uploaded"] = 1
            log.info("marker_uploaded", item_id=item_id)

    if stats["marker_uploaded"] and uploaded_tables:
        try:
            table_s = collect_table_stats(output_dir, uploaded_tables)
            update_consolidation_manifest(
                item_id=item_id,
                date_str=date_tag,
                schema_version=CURRENT_VERSION,
                table_stats=table_s,
            )
        except OSError as exc:
            log.warning("manifest_update_failed", error=str(exc))


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
        "export_failures": 0,
        "marker_uploaded": 0,
    }

    if not zips:
        log.info("nothing_to_consolidate", item_id=item_id)
        return stats

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        ndjson_dir = tmp_path / "ndjson"
        ndjson_dir.mkdir()

        db_path = tmp_path / "consolidate.duckdb"
        con = _get_connection(db_path)
        init_tables(con)

        _process_zip_entries(
            zips,
            tmp_path,
            ndjson_dir,
            item_id,
            workers=workers,
            local_zips=local_zips,
            stats=stats,
        )

        if stats["records"] == 0:
            log.warning("no_records_extracted", item_id=item_id)
            return stats

        ndjson_vr = validate_ndjson_sample(ndjson_dir)
        if not ndjson_vr.passed:
            log.error("ndjson_validation_blocked", errors=ndjson_vr.errors, item_id=item_id)
            return stats
        if ndjson_vr.warnings:
            log.warning("ndjson_validation_warnings", warnings=ndjson_vr.warnings)

        table_counts = load_and_transform(con, ndjson_dir, item_id)
        non_empty_tables = {name for name, cnt in table_counts.items() if int(cnt or 0) > 0}
        log.info("transform_complete", item_id=item_id, tables=table_counts)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        await _export_upload_and_manifest(
            con,
            output_dir,
            item_id,
            date_tag,
            non_empty_tables,
            stats,
            dry_run=dry_run,
        )

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
    dry_run: bool = typer.Option(default=False, help="Skip IA uploads"),
    workers: int = typer.Option(4, "--workers", help="Parallel ZIP processors"),
) -> None:
    """Consolidate all ZIPs for a single date into a per-date IA item."""
    zips = manifest_reader.uploaded_zips_for_date(target_date)
    item_id = f"djen-{target_date}"
    stats = asyncio.run(
        _consolidate_zips(zips, item_id, target_date, dry_run=dry_run, workers=workers)
    )
    _print_stats(stats)
    if not dry_run and stats.get("marker_uploaded", 0) > 0:
        checkpoint.mark_date_complete(target_date)


@app.command("tribunal-year")
def tribunal_year(
    tribunal: Annotated[str, typer.Argument(help="Tribunal code (e.g. TJSP)")],
    year: Annotated[int, typer.Argument(help="Year (e.g. 2026)")],
    *,
    dry_run: bool = typer.Option(default=False, help="Skip IA uploads"),
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
    dry_run: bool = typer.Option(default=False, help="Skip IA uploads"),
    workers: int = typer.Option(4, "--workers", help="Parallel ZIP processors per date"),
    max_dates: int = typer.Option(0, "--max-dates", help="Max dates per run (0 = all)"),
    deadline_seconds: int = typer.Option(600, "--deadline-seconds", help="Stop after N seconds"),
) -> None:
    """Find unconsolidated dates (newest first) and consolidate them until deadline."""
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
            _consolidate_zips(zips, item_id, target_date, dry_run=dry_run, workers=workers)
        )
        for k in total_stats:
            total_stats[k] += stats.get(k, 0)

        if not dry_run and stats.get("marker_uploaded", 0) > 0:
            checkpoint.mark_date_complete(target_date)
        processed += 1

    _print_stats(total_stats)


if __name__ == "__main__":
    app()
