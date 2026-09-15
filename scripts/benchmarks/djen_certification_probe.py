#!/usr/bin/env python3
"""Measure the extra network cost of checking a DJEN Parquet's certification
footer before a CNJ lookup — issue #1469's acceptance criterion "medir o
custo extra da inspeção do rodapé".

`web/src/lib/processoCnj.ts` now runs one extra query — `SELECT file_name,
key, value FROM parquet_kv_metadata([...])` — before the actual DJEN lookup,
to decide whether every file in the search certifies `causaganha.layout` +
`causaganha.cnj_normalization` (direct equality) or not (compatible
`regexp_replace` path). This script measures, against the real, currently
published production file (`djen-tjro-2026/comunicacoes.parquet` — not yet
certified per the 2026-09-14 audit, so this exercises the real cold-cache
DJEN request every browser visitor makes today), how much wall-clock time
that extra footer round trip costs relative to the lookup query alone —
with DuckDB's object cache both off (worst case: a fresh AsyncDuckDB
connection, as the browser does on first page load) and on (repeat visits
within the same session).

Usage:
    uv run python -m scripts.benchmarks.djen_certification_probe \\
        --output docs/planning/evidence/djen-certification-probe.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb

DEFAULT_URL = "https://archive.org/download/djen-tjro-2026/comunicacoes.parquet"
# Most-repeated CNJ in the real file (same one row_group_size_production.py's
# pilot measured — docs/planning/evidence/row-group-size-a1b-production.json,
# 64 occurrences) — a real point-lookup, not a synthetic key.
DEFAULT_CNJ = "70058285020258220014"
REPEATS = 5


@dataclass
class TimingResult:
    label: str
    object_cache: bool
    repeats: int
    seconds_per_call: list[float]
    mean_seconds: float
    median_seconds: float


def _connect(*, object_cache: bool) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"SET enable_object_cache={'true' if object_cache else 'false'}")
    return con


def _time_footer_check(url: str, *, object_cache: bool, repeats: int) -> TimingResult:
    con = _connect(object_cache=object_cache)
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        con.execute(f"SELECT file_name, key, value FROM parquet_kv_metadata(['{url}'])").fetchall()
        times.append(time.perf_counter() - t0)
        if not object_cache:
            con = _connect(object_cache=object_cache)
    return TimingResult(
        label="footer_check_only",
        object_cache=object_cache,
        repeats=repeats,
        seconds_per_call=times,
        mean_seconds=statistics.mean(times),
        median_seconds=statistics.median(times),
    )


def _time_lookup(url: str, cnj: str, *, object_cache: bool, repeats: int) -> TimingResult:
    con = _connect(object_cache=object_cache)
    sql = (
        "SELECT COUNT(*)::INTEGER AS n FROM read_parquet(['" + url + "'], union_by_name=true) "
        "WHERE regexp_replace(numero_processo, '[^0-9]', '', 'g') = ?"
    )
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        con.execute(sql, [cnj]).fetchall()
        times.append(time.perf_counter() - t0)
        if not object_cache:
            con = _connect(object_cache=object_cache)
    return TimingResult(
        label="lookup_only",
        object_cache=object_cache,
        repeats=repeats,
        seconds_per_call=times,
        mean_seconds=statistics.mean(times),
        median_seconds=statistics.median(times),
    )


def _time_footer_then_lookup(
    url: str, cnj: str, *, object_cache: bool, repeats: int
) -> TimingResult:
    sql = (
        "SELECT COUNT(*)::INTEGER AS n FROM read_parquet(['" + url + "'], union_by_name=true) "
        "WHERE regexp_replace(numero_processo, '[^0-9]', '', 'g') = ?"
    )
    times = []
    con = _connect(object_cache=object_cache)
    for _ in range(repeats):
        t0 = time.perf_counter()
        con.execute(f"SELECT file_name, key, value FROM parquet_kv_metadata(['{url}'])").fetchall()
        con.execute(sql, [cnj]).fetchall()
        times.append(time.perf_counter() - t0)
        if not object_cache:
            con = _connect(object_cache=object_cache)
    return TimingResult(
        label="footer_check_then_lookup",
        object_cache=object_cache,
        repeats=repeats,
        seconds_per_call=times,
        mean_seconds=statistics.mean(times),
        median_seconds=statistics.median(times),
    )


def run(url: str, cnj: str, repeats: int) -> dict:
    results = []
    for object_cache in (False, True):
        lookup = _time_lookup(url, cnj, object_cache=object_cache, repeats=repeats)
        footer = _time_footer_check(url, object_cache=object_cache, repeats=repeats)
        combined = _time_footer_then_lookup(url, cnj, object_cache=object_cache, repeats=repeats)
        results.extend([lookup, footer, combined])

    def _find(label: str, *, object_cache: bool) -> TimingResult:
        return next(r for r in results if r.label == label and r.object_cache == object_cache)

    marginal_cold = (
        _find("footer_check_then_lookup", object_cache=False).mean_seconds
        - _find("lookup_only", object_cache=False).mean_seconds
    )
    marginal_warm = (
        _find("footer_check_then_lookup", object_cache=True).mean_seconds
        - _find("lookup_only", object_cache=True).mean_seconds
    )
    return {
        "url": url,
        "cnj": cnj,
        "repeats": repeats,
        "results": [asdict(r) for r in results],
        "marginal_footer_cost_seconds": {
            "object_cache_off_cold_connection_per_call": marginal_cold,
            "object_cache_on_reused_connection": marginal_warm,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--cnj", default=DEFAULT_CNJ)
    parser.add_argument("--repeats", type=int, default=REPEATS)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    payload = run(args.url, args.cnj, args.repeats)
    text = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
