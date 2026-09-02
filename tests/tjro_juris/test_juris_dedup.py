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


_HISTORICAL_FIELDS = [
    "id_documento",
    "nr_processo",
    "tipo",
    "classe_judicial",
    "orgao",
    "relator",
    "sistema_origem",
    "texto_limpo",
    "url_portal",
    "extraido_em",
]

# The 9 fields #1014 wants added on top of _HISTORICAL_FIELDS (11 cols today,
# 20 once they land) — see tjro_juris.service._PARQUET_SCHEMA and issue #1014.
_NEW_FIELDS = [
    "id_processo",
    "cd_assunto_trf",
    "ds_assunto_trf",
    "cd_classe_judicial",
    "nivel_sigilo_processo",
    "grau_jurisdicao",
    "ds_md5_documento",
    "id_orgao_julgador",
    "id_orgao_julgador_colegiado",
]


def _write_parquet_with_fields(path: Path, fields: list[str], rows: list[dict]) -> None:
    schema = pa.schema(
        [pa.field(name, pa.int64() if name == "id_documento" else pa.string()) for name in fields]
    )
    table = pa.table({name: [r.get(name) for r in rows] for name in fields}, schema=schema)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)


def test_consolidate_across_narrow_then_wide_schema(tmp_path: Path) -> None:
    """A historical 10-col parquet followed by a 19-col one (#1014) must not lose columns.

    Without ``union_by_name``, DuckDB's read_parquet keys column selection off
    the FIRST file in the list: reading [narrow, wide] silently drops every
    column the narrow file lacks, instead of erroring or filling NULL.
    """
    narrow = tmp_path / "2016-01.parquet"
    _write_parquet_with_fields(
        narrow,
        _HISTORICAL_FIELDS,
        [{"id_documento": 1, "texto_limpo": "old-schema-doc", "extraido_em": "2016-01-01"}],
    )
    wide = tmp_path / "2026-01.parquet"
    _write_parquet_with_fields(
        wide,
        [*_HISTORICAL_FIELDS, *_NEW_FIELDS],
        [
            {
                "id_documento": 2,
                "texto_limpo": "new-schema-doc",
                "extraido_em": "2026-01-01",
                "id_processo": "0000001-11.2026.8.22.0000",
            }
        ],
    )
    out = tmp_path / "year.parquet"

    assert consolidate_year([narrow, wide], out) == 2

    con = duckdb.connect()
    try:
        cols = [
            d[0] for d in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{out}')").fetchall()
        ]
        rows = con.execute(
            f"SELECT id_documento, id_processo FROM read_parquet('{out}') ORDER BY id_documento"
        ).fetchall()
    finally:
        con.close()

    assert "id_processo" in cols
    assert rows == [(1, None), (2, "0000001-11.2026.8.22.0000")]


def test_consolidate_across_wide_then_narrow_schema(tmp_path: Path) -> None:
    """File order must not matter: wide-then-narrow must not raise a schema-mismatch error."""
    narrow = tmp_path / "2016-01.parquet"
    _write_parquet_with_fields(
        narrow,
        _HISTORICAL_FIELDS,
        [{"id_documento": 1, "texto_limpo": "old-schema-doc", "extraido_em": "2016-01-01"}],
    )
    wide = tmp_path / "2026-01.parquet"
    _write_parquet_with_fields(
        wide,
        [*_HISTORICAL_FIELDS, *_NEW_FIELDS],
        [
            {
                "id_documento": 2,
                "texto_limpo": "new-schema-doc",
                "extraido_em": "2026-01-01",
                "id_processo": "0000001-11.2026.8.22.0000",
            }
        ],
    )
    out = tmp_path / "year.parquet"

    assert consolidate_year([wide, narrow], out) == 2


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
