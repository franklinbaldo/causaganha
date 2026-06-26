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
    con.execute(f"CREATE VIEW src AS SELECT * FROM read_parquet([{paths}])")
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
