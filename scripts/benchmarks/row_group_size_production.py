#!/usr/bin/env python3
"""A1b — ROW_GROUP_SIZE sweep measured against a real production file.

`docs/planning/parquet-storage-optimization-plan.md` marks A1b (an
explicit, non-default `ROW_GROUP_SIZE`) as ``[speculative]`` and says not
to fix a value "sem benchmarkar contra arquivos de produção" — the
existing sweep (`scripts/benchmarks/row_group_size.py`) only ever measured
synthetic tables. This script closes that gap: it takes a real, already
published `comunicacoes.parquet` (default: `djen-tjro-2026`, the file
issue #1468/#1470/#1471's audit and pilot already use as the reference
item), re-writes it under `src/causaganha/consolidate/exporter.py`'s own
`ORDER BY numero_processo, data_disponibilizacao, id` contract at each
candidate `ROW_GROUP_SIZE`, and measures the two things that actually
matter for the epic's stated goal (fast query by CNJ, without regressing
date-range queries):

- row groups touched by a point lookup on a real, frequently-repeated CNJ
  (the target use case A1/A1b exist for)
- row groups touched by a query for a real single day (the regression A1's
  own plan explicitly warns about, now that the sort key moved from
  date-first to CNJ-first)

The currently *published* `djen-tjro-2026/comunicacoes.parquet` predates
the reorder (no `causaganha.layout` KV marker — confirmed live, schema
3.0.0 only): it is still sorted date-first. That is fine for this
benchmark; only its real row/CNJ/date distribution matters, not its
current physical order — this script re-writes it under the *candidate*
layout before measuring.

Usage:
    uv run python -m scripts.benchmarks.row_group_size_production \\
        --input /path/to/comunicacoes.parquet \\
        --output docs/planning/evidence/row-group-size-a1b-production.json
"""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb

CANDIDATE_SIZES = [16_384, 32_768, 65_536, 122_880]
DEFAULT_ROW_GROUP_SIZE = 122_880


@dataclass
class SizeMeasurement:
    row_group_size: int
    is_default: bool
    row_group_count: int
    file_bytes: int
    uncompressed_bytes: int
    compression_pct: float
    row_groups_touched_for_cnj_lookup: int
    row_groups_touched_for_one_day: int


@dataclass
class ProductionBenchmarkResult:
    source_file: str
    total_rows: int
    sample_cnj: str
    sample_cnj_occurrences: int
    sample_date: str
    total_row_groups_for_sample_date: int
    measurements: list[SizeMeasurement]


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


def _pick_sample_date(con: duckdb.DuckDBPyConnection, source: str) -> str:
    row = con.execute(
        f"""
        SELECT data_disponibilizacao::VARCHAR
        FROM read_parquet('{source}')
        GROUP BY data_disponibilizacao
        ORDER BY COUNT(*) DESC
        LIMIT 1
        """
    ).fetchone()
    return row[0]


def _row_groups_touched(con: duckdb.DuckDBPyConnection, path: Path, column: str, value: str) -> int:
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
    row_group_size: int,
    sample_cnj: str,
    sample_date: str,
) -> SizeMeasurement:
    con.execute(
        f"""
        COPY (
            SELECT * FROM read_parquet('{source}')
            ORDER BY numero_processo, data_disponibilizacao, id
        ) TO '{path}'
        (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE {row_group_size})
        """
    )

    rg_count = con.execute(
        f"SELECT COUNT(DISTINCT row_group_id) FROM parquet_metadata('{path}')"
    ).fetchone()[0]
    file_bytes = path.stat().st_size
    uncompressed = con.execute(
        f"SELECT SUM(total_uncompressed_size) FROM parquet_metadata('{path}')"
    ).fetchone()[0]

    return SizeMeasurement(
        row_group_size=row_group_size,
        is_default=row_group_size == DEFAULT_ROW_GROUP_SIZE,
        row_group_count=rg_count,
        file_bytes=file_bytes,
        uncompressed_bytes=uncompressed,
        compression_pct=round(100 * file_bytes / uncompressed, 1) if uncompressed else 0.0,
        row_groups_touched_for_cnj_lookup=_row_groups_touched(
            con, path, "numero_processo", sample_cnj
        ),
        row_groups_touched_for_one_day=_row_groups_touched(
            con, path, "data_disponibilizacao", sample_date
        ),
    )


def run(source: str) -> ProductionBenchmarkResult:
    con = duckdb.connect()
    total_rows = con.execute(f"SELECT COUNT(*) FROM read_parquet('{source}')").fetchone()[0]
    sample_cnj, occurrences = _pick_sample_cnj(con, source)
    sample_date = _pick_sample_date(con, source)
    total_row_groups_for_sample_date = con.execute(
        f"""
        SELECT COUNT(DISTINCT row_group_id) FROM parquet_metadata('{source}')
        """
    ).fetchone()[0]

    measurements = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for rgs in CANDIDATE_SIZES:
            path = Path(tmpdir) / f"candidate_{rgs}.parquet"
            measurements.append(_write_and_measure(con, source, path, rgs, sample_cnj, sample_date))
    con.close()

    return ProductionBenchmarkResult(
        source_file=source,
        total_rows=total_rows,
        sample_cnj=sample_cnj,
        sample_cnj_occurrences=occurrences,
        sample_date=sample_date,
        total_row_groups_for_sample_date=total_row_groups_for_sample_date,
        measurements=measurements,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to a real comunicacoes.parquet")
    parser.add_argument("--output", required=True, help="Where to write the JSON evidence")
    args = parser.parse_args()

    result = run(args.input)

    payload = asdict(result)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n")

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
