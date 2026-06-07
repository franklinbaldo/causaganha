"""A1b — ROW_GROUP_SIZE sweep benchmark.

Tests how different ROW_GROUP_SIZE values affect:
  - File size
  - Row-group count
  - Selective query cost (rows scanned for a tight date predicate)
  - Full-scan cost (all rows)

Two synthetic item classes are benchmarked:
  - "small"  : 50K rows  — fits in one default (122880) group
  - "medium" : 300K rows — already has multiple default groups
  - "large"  : 1M rows   — typical big tribunal-year

ROW_GROUP_SIZE values tested: 8192, 16384, 32768, 65536, 122880 (default).

Usage:
    uv run python scripts/benchmarks/row_group_size.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb


SIZES = [8_192, 16_384, 32_768, 65_536, 122_880]
ITEM_CLASSES = {
    "small": 50_000,
    "medium": 300_000,
    "large": 1_000_000,
}
DAYS = 365


def _create_table(con: duckdb.DuckDBPyConnection, n_rows: int) -> None:
    con.execute("DROP TABLE IF EXISTS t")
    con.execute(
        f"""
        CREATE TABLE t AS
        SELECT
            printf('%020d', (range * 7) % {max(n_rows // 10, 1)}) AS numero_processo,
            DATE '2025-01-01' + INTERVAL ((range * 13) % {DAYS}) DAY AS data_disponibilizacao,
            gen_random_uuid()::VARCHAR AS id
        FROM range({n_rows})
        """
    )


def _write_and_measure(
    con: duckdb.DuckDBPyConnection,
    path: Path,
    rgs: int,
) -> dict:
    opts = f"FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE {rgs}"
    con.execute(f"COPY (SELECT * FROM t ORDER BY data_disponibilizacao) TO '{path}' ({opts})")

    # Structure
    rg_count = con.execute(
        f"SELECT COUNT(DISTINCT row_group_id) FROM parquet_metadata('{path}')"
    ).fetchone()[0]
    file_bytes = path.stat().st_size

    # Selective query cost: single day, mid-year
    target_date = "2025-07-01"
    rows_scanned = _count_row_groups_touched(con, path, target_date)

    # Compression ratio
    uncomp = con.execute(
        f"SELECT SUM(total_uncompressed_size) FROM parquet_metadata('{path}')"
    ).fetchone()[0]

    return {
        "rg_count": rg_count,
        "file_bytes": file_bytes,
        "uncompressed": uncomp,
        "rows_scanned_for_1day": rows_scanned,
    }


def _count_row_groups_touched(con: duckdb.DuckDBPyConnection, path: Path, date: str) -> int:
    """Row groups whose [min,max] overlaps date — a proxy for HTTP ranges downloaded."""
    return con.execute(
        f"""
        SELECT COUNT(*)
        FROM parquet_metadata('{path}')
        WHERE path_in_schema = 'data_disponibilizacao'
          AND (stats_min_value IS NULL
               OR (stats_min_value <= '{date}' AND stats_max_value >= '{date}'))
        """
    ).fetchone()[0]


def _human(n: int) -> str:
    if n >= 1_048_576:
        return f"{n / 1_048_576:.2f} MiB"
    if n >= 1_024:
        return f"{n / 1_024:.1f} KiB"
    return f"{n} B"


def run() -> None:
    print(f"duckdb {duckdb.__version__}")
    print()
    for class_name, n_rows in ITEM_CLASSES.items():
        print(f"{'=' * 72}")
        print(f"Item class: {class_name} ({n_rows:,} rows)")
        print(f"{'=' * 72}")
        print(
            f"{'ROW_GROUP_SIZE':>15} {'RG count':>9} {'File size':>12} "
            f"{'Compressed%':>12} {'RGs for 1 day':>14}"
        )
        print("-" * 70)

        con = duckdb.connect()
        _create_table(con, n_rows)

        with tempfile.TemporaryDirectory() as tmpdir:
            for rgs in SIZES:
                path = Path(tmpdir) / f"t_{rgs}.parquet"
                m = _write_and_measure(con, path, rgs)
                ratio = (
                    round(100 * m["file_bytes"] / m["uncompressed"], 1) if m["uncompressed"] else 0
                )
                default_marker = " ← default" if rgs == 122_880 else ""
                print(
                    f"{rgs:>15,} {m['rg_count']:>9} {_human(m['file_bytes']):>12} "
                    f"{ratio:>11.1f}% {m['rows_scanned_for_1day']:>14}{default_marker}"
                )
        con.close()
        print()


if __name__ == "__main__":
    run()
