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
from causaganha.consolidate.candidates import (
    dates_at_current_version,
    dates_needing_consolidation_from_ia,
    dates_needing_reconsolidation,
)
from causaganha.consolidate.consolidation_manifest import (
    collect_table_stats,
    update_consolidation_manifest,
)
from causaganha.consolidate.exporter import (
    _upload_consolidated,
    export_table_sync,
    upload_marker,
)
from causaganha.consolidate.ndjson_validator import validate_ndjson_sample
from causaganha.consolidate.schema_registry import CURRENT_VERSION
from causaganha.consolidate.transforms import TABLES, init_tables, load_and_transform
from causaganha.consolidate.validation import validate_parquet, validate_roundtrip_equivalence
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


def _uploads_complete(
    non_empty_tables: set[str],
    stats: dict[str, int | float],
    item_id: str,
) -> bool:
    """Return true only when every non-empty table was uploaded to IA."""
    expected = len(non_empty_tables)
    if stats["uploaded"] == expected and stats["export_failures"] == 0:
        return True

    log.error(
        "marker_blocked_by_incomplete_uploads",
        item_id=item_id,
        expected=expected,
        uploaded=stats["uploaded"],
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
    ndjson_dir: Path | None = None,
) -> None:
    """Export all tables, validate, upload, write marker, and update manifest."""
    # 1. Export all tables locally and run validate_parquet on each
    local_exports = []
    for table_name in TABLES:
        try:
            export_result = await asyncio.to_thread(
                export_table_sync,
                table_name,
                con,
                output_dir,
                item_id,
            )
        except Exception as exc:
            log.error("table_export_error", table=table_name, error=str(exc))
            if table_name in non_empty_tables:
                stats["export_failures"] += 1
            continue

        if export_result is not None:
            output_path, size_mb, count = export_result
            log.info(
                "parquet_created",
                table=table_name,
                rows=count,
                size_mb=f"{size_mb:.1f}",
            )
            # Validate parquet
            vr = await asyncio.to_thread(validate_parquet, output_path, table_name)
            if not vr.passed:
                log.error("validation_blocked_upload", table=table_name, errors=vr.errors)
                if table_name in non_empty_tables:
                    stats["export_failures"] += 1
                raise ValueError(f"Parquet validation failed for table '{table_name}': {vr.errors}")
            if vr.warnings:
                log.warning("validation_warnings", table=table_name, warnings=vr.warnings)

            local_exports.append((table_name, output_path, size_mb))
            stats["parquets_created"] += 1

    # 2. Run roundtrip equivalence gate!
    if ndjson_dir is not None:
        log.info("running_roundtrip_equivalence_gate", item_id=item_id)
        validate_roundtrip_equivalence(ndjson_dir, output_dir)
        log.info("roundtrip_equivalence_gate_passed", item_id=item_id)

    # 3. Upload Parquet files to IA (if not dry_run)
    ia_auth = get_ia_s3_auth() or ""
    if not ia_auth and not dry_run:
        log.warning("ia_credentials_not_found", hint="Set IAS3_ACCESS_KEY/IAS3_SECRET_KEY")
        return

    breaker = CircuitBreaker(threshold=5)
    uploaded_tables = []

    async with create_upload_client(ia_auth) as client:
        for table_name, output_path, size_mb in local_exports:
            uploaded = 0
            if not dry_run:
                success = await _upload_consolidated(
                    client,
                    item_id,
                    output_path,
                    date_tag,
                    circuit_breaker=breaker,
                )
                if success:
                    uploaded = 1
                    log.info("uploaded", table=table_name)
                    uploaded_tables.append(table_name)
                    stats["uploaded"] += 1
                    stats["uploaded_mb"] += size_mb
                elif table_name in non_empty_tables:
                    stats["export_failures"] += 1
            else:
                stats["uploaded_mb"] += size_mb

        if _uploads_complete(non_empty_tables, stats, item_id) and (
            (stats["uploaded"] > 0 or dry_run)
            and (dry_run or await upload_marker(client, item_id, date_tag, circuit_breaker=breaker))
        ):
            stats["marker_uploaded"] = 1
            log.info("marker_uploaded", item_id=item_id)

    if stats["marker_uploaded"] and (uploaded_tables or dry_run):
        try:
            # For dry runs, we don't upload but we can still register stats of non-empty tables to manifest
            manifest_tables = uploaded_tables or list(non_empty_tables)
            table_s = collect_table_stats(output_dir, manifest_tables)
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
            ndjson_dir=ndjson_dir,
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


def _run_date_batch(
    dates: list[str],
    *,
    dry_run: bool,
    workers: int,
    max_dates: int,
    deadline_seconds: int,
    skip_checkpoint: bool = False,
) -> dict[str, int | float]:
    """Process a batch of dates with deadline and max-dates limits."""
    start = time.monotonic()
    current_version_dates = dates_at_current_version()

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
            log.info("batch_max_dates_reached", processed=processed)
            break
        if time.monotonic() - start > deadline_seconds:
            log.info("batch_deadline_reached", elapsed=time.monotonic() - start)
            break
        if not skip_checkpoint and checkpoint.is_date_completed(target_date):
            log.info("batch_already_done", date=target_date)
            continue
        if target_date in current_version_dates:
            log.info("batch_current_version", date=target_date)
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

    return total_stats


@app.command()
def backfill(
    *,
    dry_run: bool = typer.Option(default=False, help="Skip IA uploads"),
    workers: int = typer.Option(4, "--workers", help="Parallel ZIP processors per date"),
    max_dates: int = typer.Option(0, "--max-dates", help="Max dates per run (0 = all)"),
    deadline_seconds: int = typer.Option(600, "--deadline-seconds", help="Stop after N seconds"),
) -> None:
    """Find unconsolidated dates (newest first) and consolidate them until deadline."""
    dates = dates_needing_consolidation_from_ia()
    log.info("backfill_candidates", count=len(dates))
    total_stats = _run_date_batch(
        dates,
        dry_run=dry_run,
        workers=workers,
        max_dates=max_dates,
        deadline_seconds=deadline_seconds,
    )
    _print_stats(total_stats)


@app.command()
def reconsolidate(
    *,
    dry_run: bool = typer.Option(default=False, help="Skip IA uploads"),
    workers: int = typer.Option(4, "--workers", help="Parallel ZIP processors per date"),
    max_dates: int = typer.Option(0, "--max-dates", help="Max dates per run (0 = all)"),
    deadline_seconds: int = typer.Option(600, "--deadline-seconds", help="Stop after N seconds"),
) -> None:
    """Re-consolidate dates with an older schema version (newest first)."""
    dates = dates_needing_reconsolidation()
    log.info("reconsolidate_candidates", count=len(dates))
    if not dates:
        log.info("reconsolidate_nothing_to_do")
        return
    total_stats = _run_date_batch(
        dates,
        dry_run=dry_run,
        workers=workers,
        max_dates=max_dates,
        deadline_seconds=deadline_seconds,
        skip_checkpoint=True,
    )
    _print_stats(total_stats)


if __name__ == "__main__":
    app()
