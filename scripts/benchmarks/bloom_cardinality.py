"""Measure when DuckDB's Parquet writer emits a bloom filter for a column.

DuckDB writes a per-column Parquet bloom filter only for row groups it
dictionary-encodes, and the dictionary decision is made **per row group**
from the distinct values *within that group* — not from global cardinality.
Physical ordering therefore changes the outcome: sorting by the column packs
a narrow value range into each row group, so even a globally high-cardinality
column gets dictionary-encoded (and bloom-filtered) when sorted by it.

This sweeps (ordering x global cardinality x row-group size) with the row
count fixed, and reports, per case: row-group count, how many row groups got
a bloom filter, and the column encodings. Used to justify section 1c of the
parquet-storage-optimization plan: a numero_processo point lookup gets bloom
help **only when the file is sorted by numero_processo**; when the file is
sorted by date (scattering numero_processo), no bloom filter is written.
"""

from __future__ import annotations

import duckdb


ROWS = 500_000


def measure(con: duckdb.DuckDBPyConnection, card: int, order: str, rgs: int | None) -> dict:
    con.execute("DROP TABLE IF EXISTS t")
    con.execute(
        f"""CREATE TABLE t AS
        SELECT printf('%020d', (range * 7) % {card}) AS numero_processo
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
    print(f"{'ordering':24} {'cardinality':>11} {'rgs':>7}  groups/bloom  encodings")
    for order in ("", "numero_processo"):
        label = order or "(shuffled)"
        for card in (100, 100_000, ROWS):
            for rgs in (None, 16_384):
                m = measure(con, card, order, rgs)
                print(
                    f"{label:24} {card:>11} {rgs!s:>7}  "
                    f"{m['row_groups']:>3}/{m['with_bloom']:<3}      {m['encodings']}"
                )


if __name__ == "__main__":
    run()
