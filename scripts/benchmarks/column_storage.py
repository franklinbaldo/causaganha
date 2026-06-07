"""A0 — column storage measurement.

Reports compressed bytes per column for a Parquet file (local or HTTP URL),
including row-group structure and encoding choices.  Run this against a
representative set of IA items before deciding on A2/A3 schema migrations.

Usage:
    # Local file
    uv run python scripts/benchmarks/column_storage.py output/comunicacoes.parquet

    # IA item over HTTPS (requires httpfs)
    uv run python scripts/benchmarks/column_storage.py \\
        https://archive.org/download/djen-tjsp-2025/comunicacoes.parquet

    # All tables in a local output directory
    uv run python scripts/benchmarks/column_storage.py --dir /tmp/djen-tjsp-2025/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb


def _load_httpfs(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("INSTALL httpfs; LOAD httpfs;")


def analyze_file(path: str, *, use_httpfs: bool = False) -> None:
    con = duckdb.connect()
    if use_httpfs:
        _load_httpfs(con)

    print(f"\n{'='*72}")
    print(f"File: {path}")
    print(f"{'='*72}")

    # Row and row-group counts
    rg_meta = con.execute(
        f"""
        SELECT COUNT(DISTINCT row_group_id) AS rg_count,
               SUM(num_values) AS total_rows
        FROM parquet_metadata('{path}')
        """
    ).fetchone()
    rg_count, total_rows = rg_meta
    print(f"Row groups : {rg_count}")
    print(f"Total rows : {total_rows:,}")
    print()

    # Per-column breakdown
    col_data = con.execute(
        f"""
        SELECT
            path_in_schema                          AS column,
            COUNT(*)                                AS row_groups,
            SUM(total_compressed_size)              AS compressed_bytes,
            SUM(total_uncompressed_size)            AS uncompressed_bytes,
            ROUND(100.0 * SUM(total_compressed_size) /
                  NULLIF(SUM(total_uncompressed_size), 0), 1) AS compression_pct,
            STRING_AGG(DISTINCT encodings, ', ')    AS encodings,
            SUM(CASE WHEN bloom_filter_offset IS NOT NULL THEN 1 ELSE 0 END) AS bloom_rgs
        FROM parquet_metadata('{path}')
        GROUP BY path_in_schema
        ORDER BY compressed_bytes DESC
        """
    ).fetchall()

    total_compressed = sum(r[2] for r in col_data)
    print(f"{'Column':<35} {'Compressed':>12} {'%total':>7} {'Ratio':>7} {'Bloom':>6}  Encodings")
    print("-" * 90)
    for col, rgs, compressed, uncompressed, ratio, encodings, bloom in col_data:
        pct = 100.0 * (compressed or 0) / total_compressed if total_compressed else 0
        print(
            f"{col:<35} {_human(compressed):>12} {pct:>6.1f}% "
            f"{ratio or 0:>6.1f}% {bloom:>6}  {encodings or ''}"
        )
    print("-" * 90)
    print(f"{'TOTAL':<35} {_human(total_compressed):>12}")

    # Min/max range check for date columns (pruning quality)
    date_cols = [r[0] for r in col_data if "data" in r[0] or "date" in r[0] or "first_seen" in r[0]]
    if date_cols:
        print()
        print("Date column min/max per row group (pruning quality):")
        for col in date_cols[:3]:
            ranges = con.execute(
                f"""
                SELECT row_group_id,
                       stats_min_value, stats_max_value
                FROM parquet_metadata('{path}')
                WHERE path_in_schema = '{col}'
                ORDER BY row_group_id
                LIMIT 8
                """
            ).fetchall()
            if ranges and ranges[0][1] is not None:
                print(f"  {col}:")
                for rg_id, mn, mx in ranges:
                    print(f"    rg {rg_id}: {mn} → {mx}")

    con.close()


def analyze_dir(directory: str, *, use_httpfs: bool = False) -> None:
    d = Path(directory)
    parquets = sorted(d.glob("*.parquet"))
    if not parquets:
        print(f"No .parquet files found in {directory}")
        return
    for p in parquets:
        analyze_file(str(p), use_httpfs=use_httpfs)


def _human(n: int | None) -> str:
    if n is None:
        return "N/A"
    if n >= 1_048_576:
        return f"{n/1_048_576:.1f} MiB"
    if n >= 1_024:
        return f"{n/1_024:.1f} KiB"
    return f"{n} B"


def main() -> None:
    ap = argparse.ArgumentParser(description="A0: column-level Parquet storage analysis")
    ap.add_argument("path", nargs="?", help="Parquet file or HTTP URL")
    ap.add_argument("--dir", help="Directory of .parquet files")
    args = ap.parse_args()

    if not args.path and not args.dir:
        ap.print_help()
        sys.exit(1)

    use_httpfs = args.path and args.path.startswith("http")

    if args.dir:
        analyze_dir(args.dir, use_httpfs=False)
    else:
        analyze_file(args.path, use_httpfs=use_httpfs)


if __name__ == "__main__":
    main()
