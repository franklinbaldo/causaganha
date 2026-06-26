"""Dedup logic for STJ acórdãos JSON files using DuckDB."""

from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb


if TYPE_CHECKING:
    from pathlib import Path
import structlog


log = structlog.get_logger()


def dedup_acordaos(input_paths: list[Path], output_path: Path) -> int:
    """Load all JSON files, dedup by ``id`` keeping latest by ``data_extracao``.

    Writes a parquet file at *output_path* and returns the count of
    deduplicated records.

    Args:
        input_paths: List of JSON file paths to ingest.
        output_path: Destination parquet path.

    Returns:
        Number of records written after deduplication.
    """
    if not input_paths:
        log.warning("stj_dedup_no_input_files")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build a quoted, comma-separated list of glob-safe paths for DuckDB
    path_list = ", ".join(f"'{p}'" for p in input_paths)

    con = duckdb.connect()
    try:
        # Load all JSON files, dedup by id keeping the row with the latest data_extracao
        con.execute(f"""
            CREATE TABLE acordaos AS
            SELECT *
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY id
                        ORDER BY data_extracao DESC NULLS LAST
                    ) AS _rn
                FROM read_json([{path_list}], auto_detect=true, union_by_name=true)
            )
            WHERE _rn = 1
        """)
        con.execute("ALTER TABLE acordaos DROP COLUMN _rn")
        count: int = con.execute("SELECT COUNT(*) FROM acordaos").fetchone()[0]
        con.execute(f"COPY acordaos TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    finally:
        con.close()

    log.info("stj_dedup_complete", input_count=len(input_paths), output_count=count, dest=str(output_path))
    return count
