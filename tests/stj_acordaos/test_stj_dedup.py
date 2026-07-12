"""Tests for stj_acordaos.dedup — dedup key, collisions, idempotency."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import duckdb

from stj_acordaos.dedup import dedup_acordaos


if TYPE_CHECKING:
    from pathlib import Path


def _write_json(path: Path, records: list[dict]) -> None:
    path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")


def _read_parquet(path: Path) -> list[dict]:
    con = duckdb.connect()
    try:
        rows = con.execute(f"SELECT * FROM read_parquet('{path}') ORDER BY id").fetchall()
        cols = [
            d[0] for d in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path}')").fetchall()
        ]
    finally:
        con.close()
    return [dict(zip(cols, row, strict=True)) for row in rows]


def test_empty_input_returns_zero(tmp_path: Path) -> None:
    out = tmp_path / "out.parquet"
    assert dedup_acordaos([], out) == 0
    assert not out.exists()


def test_no_collisions_keeps_all_records(tmp_path: Path) -> None:
    f1 = tmp_path / "acordaos-2024-01.json"
    f2 = tmp_path / "acordaos-2024-02.json"
    _write_json(f1, [{"id": "A1", "ementa": "primeira"}, {"id": "A2", "ementa": "segunda"}])
    _write_json(f2, [{"id": "A3", "ementa": "terceira"}])
    out = tmp_path / "out.parquet"

    assert dedup_acordaos([f1, f2], out) == 3
    rows = _read_parquet(out)
    assert sorted(r["id"] for r in rows) == ["A1", "A2", "A3"]


def test_collision_keeps_record_from_latest_source_file(tmp_path: Path) -> None:
    """Same ``id`` in two files: the row from the lexicographically latest file wins."""
    f1 = tmp_path / "acordaos-2024-01.json"
    f2 = tmp_path / "acordaos-2024-02.json"
    _write_json(f1, [{"id": "A1", "ementa": "versao antiga"}])
    _write_json(f2, [{"id": "A1", "ementa": "versao nova"}])
    out = tmp_path / "out.parquet"

    assert dedup_acordaos([f1, f2], out) == 1
    rows = _read_parquet(out)
    assert rows[0]["ementa"] == "versao nova"


def test_collision_winner_independent_of_input_order(tmp_path: Path) -> None:
    """Dedup key is ``id`` ordered by source filename — not by list position."""
    f1 = tmp_path / "acordaos-2024-01.json"
    f2 = tmp_path / "acordaos-2024-02.json"
    _write_json(f1, [{"id": "A1", "ementa": "versao antiga"}])
    _write_json(f2, [{"id": "A1", "ementa": "versao nova"}])
    out = tmp_path / "out.parquet"

    # Pass the newer file FIRST: winner must still be the newer file's row.
    assert dedup_acordaos([f2, f1], out) == 1
    rows = _read_parquet(out)
    assert rows[0]["ementa"] == "versao nova"


def test_helper_columns_are_dropped(tmp_path: Path) -> None:
    f1 = tmp_path / "acordaos-2024-01.json"
    _write_json(f1, [{"id": "A1", "ementa": "x"}])
    out = tmp_path / "out.parquet"
    dedup_acordaos([f1], out)

    rows = _read_parquet(out)
    assert set(rows[0].keys()) == {"id", "ementa"}


def test_idempotent_rerun_produces_same_result(tmp_path: Path) -> None:
    f1 = tmp_path / "acordaos-2024-01.json"
    f2 = tmp_path / "acordaos-2024-02.json"
    _write_json(f1, [{"id": "A1", "ementa": "old"}, {"id": "A2", "ementa": "keep"}])
    _write_json(f2, [{"id": "A1", "ementa": "new"}])
    out = tmp_path / "out.parquet"

    first = dedup_acordaos([f1, f2], out)
    rows_first = _read_parquet(out)
    second = dedup_acordaos([f1, f2], out)
    rows_second = _read_parquet(out)

    assert first == second == 2
    assert rows_first == rows_second
