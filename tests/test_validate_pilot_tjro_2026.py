"""Tests for the row-order verification helpers in validate_pilot_tjro_2026.py.

These pin down the exact bug found while running the issue #1471 pilot: a
footer-only min/max overlap check cannot tell "genuinely unsorted" apart from
"a repeated numero_processo legitimately spans a row-group boundary", so the
script needs a definitive row-level check (`_sort_violations`) rather than
trusting that ambiguous footer signal as a pass/fail gate.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from scripts.validate_pilot_tjro_2026 import _footer_boundary_ties, _sort_violations


def _write_from_values(tmp_path: Path, values: list[str]) -> tuple[duckdb.DuckDBPyConnection, Path]:
    path = tmp_path / "sample.parquet"
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE t (numero_processo VARCHAR, data_disponibilizacao DATE, id VARCHAR)")
    con.executemany(
        "INSERT INTO t VALUES (?, DATE '2026-01-01', ?)",
        [(value, f"id-{i:05d}") for i, value in enumerate(values)],
    )
    # ROW_GROUP_SIZE below DuckDB's ~2048-row vector-size floor has no
    # effect; 2048 is the smallest value that reliably splits a few-thousand
    # row table into multiple physical row groups (verified empirically).
    con.execute(f"COPY t TO '{path.as_posix()}' (FORMAT PARQUET, ROW_GROUP_SIZE 2048)")
    return con, path


class TestSortViolations:
    def test_zero_for_globally_sorted_rows(self, tmp_path: Path) -> None:
        con, path = _write_from_values(tmp_path, ["001", "001", "002", "003", "003", "004"])
        assert _sort_violations(con, path) == 0

    def test_nonzero_when_a_row_reorders_the_cnj_column(self, tmp_path: Path) -> None:
        con, path = _write_from_values(tmp_path, ["001", "090", "005", "099"])
        assert _sort_violations(con, path) > 0


class TestFooterBoundaryTies:
    # DuckDB will not split a table into multiple physical row groups below
    # its internal vector-size floor (~2048 rows), regardless of the
    # ROW_GROUP_SIZE COPY option — so these fixtures need enough rows to
    # force a genuine multi-row-group file rather than trying to control the
    # split with a handful of values.
    _ROWS = 5000

    def test_true_when_duplicate_blocks_straddle_a_row_group_boundary(self, tmp_path: Path) -> None:
        # Value changes only every 10 rows — far smaller than any row-group
        # boundary DuckDB will pick over 5000 rows — so some duplicate block
        # is guaranteed to straddle a boundary while the file stays globally
        # sorted (non-decreasing).
        values = [f"{i // 10:04d}" for i in range(self._ROWS)]
        con, path = _write_from_values(tmp_path, values)
        assert _sort_violations(con, path) == 0, "fixture must itself be globally sorted"
        assert _footer_boundary_ties(con, path) is True

    def test_false_when_every_value_is_distinct(self, tmp_path: Path) -> None:
        values = [f"{i:05d}" for i in range(self._ROWS)]
        con, path = _write_from_values(tmp_path, values)
        assert _sort_violations(con, path) == 0
        assert _footer_boundary_ties(con, path) is False
