"""Deduplication utilities for TJRO JURIS parquet files."""

from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb


if TYPE_CHECKING:
    from pathlib import Path


def consolidate_year(parquet_files: list[Path], output: Path) -> int:
    """Dedup by id_documento across monthly parquets for a year. Return count."""
    if not parquet_files:
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    paths = ", ".join(f"'{p}'" for p in parquet_files)
    con = duckdb.connect()
    # union_by_name: monthly parquets accumulate columns over time (see #1014
    # — 9 fields added on top of the original schema). Without it, DuckDB
    # keys column selection off the FIRST file in the list: narrow-first
    # silently drops every column the narrow file lacks, wide-first raises
    # a schema-mismatch error. union_by_name unions by column name across
    # all files and fills missing values with NULL either way.
    con.execute(f"CREATE VIEW src AS SELECT * FROM read_parquet([{paths}], union_by_name=true)")
    con.execute(
        f"""
        COPY (
            SELECT * EXCLUDE (_rn)
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY id_documento
                        ORDER BY extraido_em DESC NULLS LAST
                    ) AS _rn
                FROM src
                WHERE id_documento IS NOT NULL
            )
            WHERE _rn = 1
        ) TO '{output}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """
    )
    return con.execute(f"SELECT COUNT(*) FROM read_parquet('{output}')").fetchone()[0]
