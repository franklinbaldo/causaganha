"""Tests for tjro_juris.dedup — dedup key, collisions, idempotency."""

from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from tjro_juris.dedup import consolidate_year


if TYPE_CHECKING:
    from pathlib import Path


def _write_parquet(path: Path, rows: list[dict]) -> None:
    schema = pa.schema(
        [
            pa.field("id_documento", pa.int64()),
            pa.field("texto_limpo", pa.string()),
            pa.field("extraido_em", pa.string()),
        ]
    )
    table = pa.table(
        {
            "id_documento": [r.get("id_documento") for r in rows],
            "texto_limpo": [r.get("texto_limpo") for r in rows],
            "extraido_em": [r.get("extraido_em") for r in rows],
        },
        schema=schema,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)


def _read_rows(path: Path) -> list[tuple]:
    con = duckdb.connect()
    try:
        return con.execute(
            f"SELECT id_documento, texto_limpo, extraido_em "
            f"FROM read_parquet('{path}') ORDER BY id_documento"
        ).fetchall()
    finally:
        con.close()


def test_empty_input_returns_zero(tmp_path: Path) -> None:
    out = tmp_path / "year.parquet"
    assert consolidate_year([], out) == 0
    assert not out.exists()


def test_dedup_keeps_latest_extraido_em(tmp_path: Path) -> None:
    f1 = tmp_path / "2024-01.parquet"
    f2 = tmp_path / "2024-02.parquet"
    _write_parquet(
        f1,
        [
            {"id_documento": 1, "texto_limpo": "v1", "extraido_em": "2024-01-31T00:00:00"},
            {"id_documento": 2, "texto_limpo": "only", "extraido_em": "2024-01-31T00:00:00"},
        ],
    )
    _write_parquet(
        f2,
        [{"id_documento": 1, "texto_limpo": "v2", "extraido_em": "2024-02-28T00:00:00"}],
    )
    out = tmp_path / "year.parquet"

    assert consolidate_year([f1, f2], out) == 2
    rows = _read_rows(out)
    assert rows[0][1] == "v2"  # id 1 → latest extraction wins
    assert rows[1][1] == "only"


def test_dedup_winner_independent_of_file_order(tmp_path: Path) -> None:
    f1 = tmp_path / "a.parquet"
    f2 = tmp_path / "b.parquet"
    _write_parquet(
        f1, [{"id_documento": 1, "texto_limpo": "new", "extraido_em": "2024-06-01T00:00:00"}]
    )
    _write_parquet(
        f2, [{"id_documento": 1, "texto_limpo": "old", "extraido_em": "2024-01-01T00:00:00"}]
    )
    out = tmp_path / "year.parquet"

    assert consolidate_year([f2, f1], out) == 1
    assert _read_rows(out)[0][1] == "new"


def test_null_id_documento_rows_are_dropped(tmp_path: Path) -> None:
    f1 = tmp_path / "2024-01.parquet"
    _write_parquet(
        f1,
        [
            {"id_documento": None, "texto_limpo": "orphan", "extraido_em": "2024-01-01"},
            {"id_documento": 5, "texto_limpo": "kept", "extraido_em": "2024-01-01"},
        ],
    )
    out = tmp_path / "year.parquet"

    assert consolidate_year([f1], out) == 1
    assert _read_rows(out) == [(5, "kept", "2024-01-01")]


def test_output_excludes_helper_column(tmp_path: Path) -> None:
    f1 = tmp_path / "2024-01.parquet"
    _write_parquet(f1, [{"id_documento": 1, "texto_limpo": "x", "extraido_em": "2024-01-01"}])
    out = tmp_path / "year.parquet"
    consolidate_year([f1], out)

    con = duckdb.connect()
    try:
        cols = [
            d[0] for d in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{out}')").fetchall()
        ]
    finally:
        con.close()
    assert "_rn" not in cols
    assert cols == ["id_documento", "texto_limpo", "extraido_em"]


def test_idempotent_reconsolidation(tmp_path: Path) -> None:
    """Consolidating the consolidated output again yields the same rows."""
    f1 = tmp_path / "2024-01.parquet"
    f2 = tmp_path / "2024-02.parquet"
    _write_parquet(f1, [{"id_documento": 1, "texto_limpo": "old", "extraido_em": "2024-01-01"}])
    _write_parquet(
        f2,
        [
            {"id_documento": 1, "texto_limpo": "new", "extraido_em": "2024-02-01"},
            {"id_documento": 2, "texto_limpo": "b", "extraido_em": "2024-02-01"},
        ],
    )
    out1 = tmp_path / "pass1.parquet"
    out2 = tmp_path / "pass2.parquet"

    count1 = consolidate_year([f1, f2], out1)
    count2 = consolidate_year([out1], out2)

    assert count1 == count2 == 2
    assert _read_rows(out1) == _read_rows(out2)
