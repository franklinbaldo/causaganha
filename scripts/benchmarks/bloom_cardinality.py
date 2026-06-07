"""Measure when DuckDB's Parquet writer emits a bloom filter for a column.

Sweeps distinct-value cardinality (with row count fixed) and checks whether
COPY ... (WRITE_BLOOM_FILTER true) actually writes a per-column bloom filter
(bloom_filter_offset non-null in parquet_metadata). Used to justify §1c of
the parquet-storage-optimization plan: high-cardinality numero_processo gets
no bloom filter regardless of the flag.
"""

from __future__ import annotations

import duckdb


ROWS = 500_000


def run() -> list[tuple[int, bool]]:
    con = duckdb.connect()
    out = []
    for card in (100, 100_000, ROWS):  # distinct values; capped at ROWS
        con.execute("DROP TABLE IF EXISTS t")
        con.execute(
            f"""CREATE TABLE t AS
            SELECT printf('%020d', (range * 7) % {card}) AS numero_processo
            FROM range({ROWS})"""
        )
        con.execute("COPY t TO '/tmp/bloom.parquet' (FORMAT PARQUET, WRITE_BLOOM_FILTER true)")
        has_bloom = con.execute(
            """SELECT bool_or(bloom_filter_offset IS NOT NULL)
               FROM parquet_metadata('/tmp/bloom.parquet')
               WHERE path_in_schema = 'numero_processo'"""
        ).fetchone()[0]
        distinct = con.execute("SELECT COUNT(DISTINCT numero_processo) FROM t").fetchone()[0]
        out.append((distinct, bool(has_bloom)))
    return out


if __name__ == "__main__":
    print(f"duckdb {duckdb.__version__}, rows={ROWS}")
    for distinct, has_bloom in run():
        print(f"  cardinality={distinct:>7}  bloom_written={has_bloom}")
