"""Export DuckDB tables → Parquet → upload to Internet Archive.

Blocking DuckDB ``COPY`` runs via ``asyncio.to_thread`` so multiple table
exports can proceed in parallel without blocking the asyncio event loop.
"""

from __future__ import annotations

import asyncio
import contextlib
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import anyio
import httpx
import structlog

from causaganha.consolidate.schema_registry import kv_metadata_sql_fragment
from causaganha.consolidate.validation import validate_parquet
from causaganha.pipeline.ia_s3 import upload_to_ia


if TYPE_CHECKING:
    import ibis

    from causaganha.pipeline.ia_s3 import CircuitBreaker


log = structlog.get_logger()


_CONSOLIDATION_META_OVERRIDES = {
    "x-archive-meta-title": "DJEN Consolidated - {date_str}",
    "x-archive-meta-description": (
        "Consolidated Parquet files from Brazilian court communications."
    ),
}


def export_table_sync(
    table_name: str,
    con: ibis.BaseBackend,
    output_dir: Path,
    item_id: str = "",
) -> tuple[Path, float, int] | None:
    """Export one DuckDB table → Parquet file with schema version stamp.

    Returns ``(output_path, size_mb, row_count)`` or ``None`` when empty.
    Blocking — call via ``asyncio.to_thread`` from async code.
    """
    t = con.table(table_name)
    count = int(t.count().execute())
    if count == 0:
        return None
    output_path = output_dir / f"{table_name}.parquet"
    kv_clause = kv_metadata_sql_fragment(item_id) if item_id else ""
    copy_opts = "FORMAT PARQUET, COMPRESSION ZSTD"
    if kv_clause:
        copy_opts = f"{copy_opts}, {kv_clause}"
    con.raw_sql(
        f"COPY {table_name} TO '{output_path}' ({copy_opts})",
    )
    size_mb = output_path.stat().st_size / (1024 * 1024)
    return output_path, size_mb, count


async def _upload_consolidated(
    client: httpx.AsyncClient,
    item_id: str,
    file_path: Path,
    date_str: str,
    circuit_breaker: CircuitBreaker | None = None,
) -> bool:
    """Upload a file to IA with consolidation-specific metadata overrides."""
    overrides = {k: v.format(date_str=date_str) for k, v in _CONSOLIDATION_META_OVERRIDES.items()}
    return await upload_to_ia(
        client,
        item_id,
        file_path,
        date_str,
        metadata_overrides=overrides,
        circuit_breaker=circuit_breaker,
    )


async def export_and_upload_table(
    table_name: str,
    con: ibis.BaseBackend,
    output_dir: Path,
    item_id: str,
    client: httpx.AsyncClient,
    date_str: str,
    *,
    dry_run: bool,
    circuit_breaker: CircuitBreaker | None = None,
) -> tuple[bool, float, int]:
    """Export a table to Parquet and upload. Returns ``(success, size_mb, uploaded)``.

    Any exception during export or upload is logged and returns ``(False, 0.0, 0)``.
    """
    try:
        export_result = await asyncio.to_thread(
            export_table_sync,
            table_name,
            con,
            output_dir,
            item_id,
        )
        if export_result is None:
            return False, 0.0, 0

        output_path, size_mb, count = export_result
        log.info(
            "parquet_created",
            table=table_name,
            rows=count,
            size_mb=f"{size_mb:.1f}",
        )

        vr = await asyncio.to_thread(validate_parquet, output_path, table_name)
        if not vr.passed:
            log.error("validation_blocked_upload", table=table_name, errors=vr.errors)
            return False, size_mb, 0
        if vr.warnings:
            log.warning("validation_warnings", table=table_name, warnings=vr.warnings)

        uploaded = 0
        if not dry_run and await _upload_consolidated(
            client,
            item_id,
            output_path,
            date_str,
            circuit_breaker=circuit_breaker,
        ):
            uploaded = 1
            log.info("uploaded", table=table_name)

    except (httpx.HTTPError, httpx.RequestError, OSError) as exc:
        log.exception("parquet_export_failed", table=table_name, error=str(exc))
        return False, 0.0, 0
    else:
        return True, size_mb, uploaded


async def upload_marker(
    client: httpx.AsyncClient,
    item_id: str,
    date_str: str,
    circuit_breaker: CircuitBreaker | None = None,
) -> bool:
    """Upload an empty ``_consolidated.marker`` file signaling completion.

    The existence of the file in the IA item is the signal — contents are
    irrelevant. Future runs check for this marker to skip already-done dates.
    """
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix="_consolidated.marker", delete=False
        ) as f:
            marker_path = Path(f.name)

        log.info("uploading_marker", item_id=item_id)
        success = await _upload_consolidated(
            client, item_id, marker_path, date_str, circuit_breaker=circuit_breaker
        )

        with contextlib.suppress(OSError):
            await anyio.Path(marker_path).unlink()

    except (httpx.HTTPError, httpx.RequestError, OSError) as exc:
        log.exception("marker_upload_failed", item_id=item_id, error=str(exc))
        return False
    else:
        return success
