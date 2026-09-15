#!/usr/bin/env python3
"""A1c -- gate the covering-index decision (plan §1c) with real production data.

`docs/planning/parquet-storage-optimization-plan.md` marks A1c
`[speculative até medir em produção]`: the only evidence that ordering by
`numero_processo` yields a Parquet bloom filter (and that ordering by
`data_disponibilizacao` does not) comes from a synthetic table
(`scripts/benchmarks/bloom_cardinality.py`), with coprime strides modelling
the real process/date correlation -- the plan explicitly says this "tem que
ser confirmada em dados reais por A1c... não cravada a partir do sintético".

This script closes that gap: it takes a real, already published
`comunicacoes.parquet` (default: `djen-tjro-2026`, the same reference item
A1b used), re-writes it under both ordering candidates --
`src/causaganha/consolidate/exporter.py`'s actual production contract
(`ORDER BY numero_processo, data_disponibilizacao, id`, `ROW_GROUP_SIZE
122880`) and the alternative date-first order it replaced -- with
`WRITE_BLOOM_FILTER true`, and inspects `parquet_metadata()` for
`bloom_filter_offset` and `encodings` per row group on the `numero_processo`
column. It also measures, for each candidate, how many row groups a real
CNJ point-lookup touches via min/max pruning alone (independent of bloom),
to show whether ordering-based pruning already reaches the ideal (1 row
group) with no need for an additive covering index.

Usage:
    uv run python -m scripts.benchmarks.bloom_filter_production \\
        --input /path/to/comunicacoes.parquet \\
        --output docs/planning/evidence/bloom-filter-a1c-production.json
"""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb

PRODUCTION_ROW_GROUP_SIZE = 122_880

CANDIDATE_ORDERINGS: dict[str, str] = {
    "cnj_first": "numero_processo, data_disponibilizacao, id",
    "date_first": "data_disponibilizacao, numero_processo, id",
}


@dataclass
class RowGroupBloomInfo:
    row_group_id: int
    encodings: str
    has_bloom_filter: bool


@dataclass
class OrderingMeasurement:
    ordering: str
    order_by: str
    row_group_count: int
    row_groups_with_bloom_filter: int
    distinct_encodings: list[str]
    row_groups_touched_for_cnj_lookup_minmax: int
    per_row_group: list[RowGroupBloomInfo]


@dataclass
class BloomFilterProductionResult:
    source_file: str
    total_rows: int
    sample_cnj: str
    sample_cnj_occurrences: int
    row_group_size: int
    measurements: list[OrderingMeasurement]
    covering_index_needed: bool
    covering_index_rationale: str


def _pick_sample_cnj(con: duckdb.DuckDBPyConnection, source: str) -> tuple[str, int]:
    row = con.execute(
        f"""
        SELECT numero_processo, COUNT(*) AS occurrences
        FROM read_parquet('{source}')
        GROUP BY numero_processo
        ORDER BY occurrences DESC
        LIMIT 1
        """
    ).fetchone()
    return row[0], row[1]


def _bloom_rows_for_column(con: duckdb.DuckDBPyConnection, path: Path, column: str) -> list[tuple]:
    return con.execute(
        f"""
        SELECT row_group_id, encodings, bloom_filter_offset
        FROM parquet_metadata('{path}')
        WHERE path_in_schema = '{column}'
        ORDER BY row_group_id
        """
    ).fetchall()


def _row_groups_touched_minmax(
    con: duckdb.DuckDBPyConnection, path: Path, column: str, value: str
) -> int:
    return con.execute(
        f"""
        SELECT COUNT(*)
        FROM parquet_metadata('{path}')
        WHERE path_in_schema = '{column}'
          AND (stats_min_value IS NULL
               OR (stats_min_value <= '{value}' AND stats_max_value >= '{value}'))
        """
    ).fetchone()[0]


def _write_and_measure(
    con: duckdb.DuckDBPyConnection,
    source: str,
    path: Path,
    ordering: str,
    order_by: str,
    row_group_size: int,
    sample_cnj: str,
) -> OrderingMeasurement:
    con.execute(
        f"""
        COPY (
            SELECT * FROM read_parquet('{source}')
            ORDER BY {order_by}
        ) TO '{path}'
        (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE {row_group_size}, WRITE_BLOOM_FILTER true)
        """
    )

    rows = _bloom_rows_for_column(con, path, "numero_processo")
    per_row_group = [
        RowGroupBloomInfo(
            row_group_id=row_group_id,
            encodings=encodings,
            has_bloom_filter=bloom_filter_offset is not None,
        )
        for row_group_id, encodings, bloom_filter_offset in rows
    ]

    return OrderingMeasurement(
        ordering=ordering,
        order_by=order_by,
        row_group_count=len(per_row_group),
        row_groups_with_bloom_filter=sum(1 for r in per_row_group if r.has_bloom_filter),
        distinct_encodings=sorted({r.encodings for r in per_row_group}),
        row_groups_touched_for_cnj_lookup_minmax=_row_groups_touched_minmax(
            con, path, "numero_processo", sample_cnj
        ),
        per_row_group=per_row_group,
    )


def decide_covering_index(measurements: list[OrderingMeasurement]) -> tuple[bool, str]:
    cnj_first = next(m for m in measurements if m.ordering == "cnj_first")
    if cnj_first.row_groups_touched_for_cnj_lookup_minmax <= 1:
        return (
            False,
            "ORDER BY numero_processo (cnj_first, o layout real de exporter.py) já poda o "
            "point-lookup por CNJ a 1 row group via min/max stats sozinho, com ou sem bloom "
            "filter -- o índice covering aditivo não traria ganho de pruning mensurável para "
            "este acesso.",
        )
    return (
        True,
        "ORDER BY numero_processo não reduziu o point-lookup por CNJ a 1 row group via "
        "min/max -- min/max pruning sozinho não basta; um índice covering aditivo (ou "
        "bloom filter, se presente) seria necessário para evitar full-scan neste acesso.",
    )


def run(source: str, row_group_size: int) -> BloomFilterProductionResult:
    con = duckdb.connect()
    total_rows = con.execute(f"SELECT COUNT(*) FROM read_parquet('{source}')").fetchone()[0]
    sample_cnj, occurrences = _pick_sample_cnj(con, source)

    measurements = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for ordering, order_by in CANDIDATE_ORDERINGS.items():
            path = Path(tmpdir) / f"candidate_{ordering}.parquet"
            measurements.append(
                _write_and_measure(
                    con, source, path, ordering, order_by, row_group_size, sample_cnj
                )
            )
    con.close()

    covering_index_needed, rationale = decide_covering_index(measurements)

    return BloomFilterProductionResult(
        source_file=source,
        total_rows=total_rows,
        sample_cnj=sample_cnj,
        sample_cnj_occurrences=occurrences,
        row_group_size=row_group_size,
        measurements=measurements,
        covering_index_needed=covering_index_needed,
        covering_index_rationale=rationale,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to a real comunicacoes.parquet")
    parser.add_argument("--output", required=True, help="Where to write the JSON evidence")
    parser.add_argument("--row-group-size", type=int, default=PRODUCTION_ROW_GROUP_SIZE)
    args = parser.parse_args()

    result = run(args.input, args.row_group_size)

    payload = asdict(result)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n")

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
