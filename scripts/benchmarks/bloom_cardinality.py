"""Measure when DuckDB's Parquet writer emits a bloom filter for a column.

DuckDB writes a per-column Parquet bloom filter only for row groups it
dictionary-encodes, and the dictionary decision is made **per row group**
from the distinct values *within that group* — not from global cardinality.
Physical ordering therefore changes the outcome: sorting by the column packs
a narrow value range into each row group, so even a globally high-cardinality
column gets dictionary-encoded (and bloom-filtered) when sorted by it.

This sweeps (ordering x global cardinality x row-group size) with the row
count fixed, and reports, per case: row-group count, how many row groups got
a bloom filter for ``numero_processo``, and the column encodings.

Synthetic-data caveat: the table has both a ``data`` (date) column and a
``numero_processo`` column. Real DJEN data has thousands of distinct
processes per day and a given process's communications scattered across the
year, so date ordering does **not** cluster a process's rows — modelled here
by making ``data`` and ``numero_processo`` use coprime strides so ordering by
date leaves the process column scattered. This is a model, not production:
section 1c's date-ordered conclusion must still be confirmed on real items
(task A0). Used to justify section 1c of the parquet-storage-optimization
plan.
"""

from __future__ import annotations

import duckdb


ROWS = 500_000
DAYS = 365  # spread rows across a year of dates


def measure(con: duckdb.DuckDBPyConnection, card: int, order: str, rgs: int | None) -> dict:
    con.execute("DROP TABLE IF EXISTS t")
    # numero_processo: `card` distinct values, stride 7.
    # data: spread over DAYS, stride 13 (coprime with 7) so ordering by data
    # leaves numero_processo scattered, as in real DJEN (many processes/day).
    con.execute(
        f"""CREATE TABLE t AS
        SELECT
            printf('%020d', (range * 7) % {card}) AS numero_processo,
            DATE '2025-01-01' + INTERVAL ((range * 13) % {DAYS}) DAY AS data
        FROM range({ROWS})"""
    )
    opts = "FORMAT PARQUET, WRITE_BLOOM_FILTER true"
    if rgs is not None:
        opts += f", ROW_GROUP_SIZE {rgs}"
    order_sql = f"ORDER BY {order}" if order else ""
    con.execute(f"COPY (SELECT * FROM t {order_sql}) TO '/tmp/bloom.parquet' ({opts})")
    rg_count, with_bloom = con.execute(
        """SELECT COUNT(*),
                  SUM(CASE WHEN bloom_filter_offset IS NOT NULL THEN 1 ELSE 0 END)
           FROM parquet_metadata('/tmp/bloom.parquet')
           WHERE path_in_schema = 'numero_processo'"""
    ).fetchone()
    encodings = [
        r[0]
        for r in con.execute(
            """SELECT DISTINCT encodings FROM parquet_metadata('/tmp/bloom.parquet')
               WHERE path_in_schema = 'numero_processo'"""
        ).fetchall()
    ]
    return {"row_groups": rg_count, "with_bloom": with_bloom, "encodings": encodings}


def run() -> None:
    con = duckdb.connect()
    print(f"duckdb {duckdb.__version__}, rows={ROWS}")
    print(f"{'ordering':22} {'cardinality':>11} {'rgs':>7}  groups/bloom  encodings")
    for order in ("data", "numero_processo"):
        for card in (100, 100_000, ROWS):
            for rgs in (None, 16_384):
                m = measure(con, card, order, rgs)
                print(
                    f"ORDER BY {order:13} {card:>11} {rgs!s:>7}  "
                    f"{m['row_groups']:>3}/{m['with_bloom']:<3}      {m['encodings']}"
                )


if __name__ == "__main__":
    run()
