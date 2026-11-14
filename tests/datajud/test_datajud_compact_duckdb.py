"""DuckDB compaction (#1708) must reproduce the delta-by-delta Python merge.

The reference is the previous implementation: apply each delta batch in order
with :func:`merge_capa_rows` / :func:`merge_movimento_rows`. The DuckDB path
reads Parquet files directly and never materialises the canonical in Python.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow.parquet as pq

from datajud import archive
from datajud.cdc import compact_deltas, read_parquet_rows
from datajud.dedup import capa_row_key, merge_capa_rows, merge_movimento_rows


if TYPE_CHECKING:
    from pathlib import Path


T = "tjro"


def _capa(
    cnj: str, grau: str, codigo: int | None, upd: str, *, nome: str = "Vara", n: int = 1
) -> dict:
    return {
        "numero_processo": cnj,
        "tribunal": "TJRO",
        "grau": grau,
        "orgao_julgador_codigo": codigo,
        "orgao_julgador": nome,
        "classe_codigo": 7,
        "classe_nome": "Classe",
        "assuntos": "[]",
        "sistema": "PJe",
        "formato": "Eletrônico",
        "nivel_sigilo": 0,
        "data_ajuizamento": "2024-01-01",
        "ultima_atualizacao": upd,
        "n_movimentos": n,
        "consultado_em": upd,
    }


def _mov(cnj: str, grau: str, codigo: int | None, mov_code: int, when: str) -> dict:
    return {
        "numero_processo": cnj,
        "tribunal": "TJRO",
        "grau": grau,
        "orgao_julgador_codigo": codigo,
        "codigo": mov_code,
        "nome": f"mov {mov_code}",
        "data_hora": when,
        "complementos": "[]",
    }


def _write_batches(root: Path, existing: tuple[list, list], batches: list[tuple[list, list]]):
    canonical = root / "canonical"
    deltas = root / "deltas" / T
    deltas.mkdir(parents=True)
    archive.write_capa_parquet(existing[0], canonical / archive.capa_parquet_name(T), tribunal=T)
    archive.write_movimentos_parquet(
        existing[1], canonical / archive.movimentos_parquet_name(T), tribunal=T
    )
    for seq, (capas, movs) in enumerate(batches, 1):
        archive.write_capa_parquet(capas, deltas / f"capa_delta_{T}_{seq:06d}.parquet", tribunal=T)
        archive.write_movimentos_parquet(
            movs, deltas / f"mov_delta_{T}_{seq:06d}.parquet", tribunal=T
        )
    return canonical, root / "deltas"


def _reference(existing: tuple[list, list], batches: list[tuple[list, list]]):
    capas, movs = existing
    for batch_capas, batch_movs in batches:
        refreshed = {capa_row_key(r) for r in batch_capas}
        capas = merge_capa_rows(capas, batch_capas)
        movs = merge_movimento_rows(movs, batch_movs, refreshed)
    return capas, movs


def _norm(rows: list[dict], schema) -> list[tuple]:
    return sorted(tuple(row.get(name) for name in schema.names) for row in rows)


def test_matches_python_merge_across_batches(tmp_path: Path):
    a, b, c = "00000010220248220001", "00000020320248220002", "00000030420248220003"
    existing = (
        [_capa(a, "G1", 1, "2026-01-01"), _capa(b, "G1", 2, "2026-01-01")],
        [
            _mov(a, "G1", 1, 10, "2026-01-01"),
            _mov(a, "G1", 1, 11, "2026-01-02"),
            _mov(b, "G1", 2, 20, "2026-01-01"),
        ],
    )
    batches = [
        # a refreshed (newer), c new, a in G2 is a distinct document
        (
            [
                _capa(a, "G1", 1, "2026-02-01", n=1),
                _capa(c, "G1", 3, "2026-02-01"),
                _capa(a, "G2", 9, "2026-02-01"),
            ],
            [
                _mov(a, "G1", 1, 12, "2026-02-01"),
                _mov(c, "G1", 3, 30, "2026-02-01"),
                _mov(a, "G2", 9, 90, "2026-02-01"),
            ],
        ),
        # tie on b: the later occurrence wins; a appears with an *older* timestamp
        (
            [_capa(b, "G1", 2, "2026-01-01", nome="Vara nova"), _capa(a, "G1", 1, "2026-01-15")],
            [_mov(b, "G1", 2, 21, "2026-01-01"), _mov(a, "G1", 1, 13, "2026-01-15")],
        ),
        # c refreshed with zero movements
        ([_capa(c, "G1", 3, "2026-03-01", n=0)], []),
    ]
    canonical, deltas = _write_batches(tmp_path, existing, batches)

    capa_path, mov_path, n_capa, n_mov = compact_deltas(
        T, deltas_dir=deltas, canonical_dir=canonical
    )

    ref_capas, ref_movs = _reference(existing, batches)
    assert _norm(read_parquet_rows(capa_path), archive.CAPA_SCHEMA) == _norm(
        ref_capas, archive.CAPA_SCHEMA
    )
    assert _norm(read_parquet_rows(mov_path), archive.MOVIMENTOS_SCHEMA) == _norm(
        ref_movs, archive.MOVIMENTOS_SCHEMA
    )
    assert (n_capa, n_mov) == (len(ref_capas), len(ref_movs))
    # deltas consumed
    assert not list((deltas / T).glob("*_delta_*.parquet"))


def test_null_codigo_refresh_replaces_movements_instead_of_duplicating(tmp_path: Path):
    """The Python merge never matched null-código movements to their capa key."""
    a = "00000010220248220001"
    existing = ([_capa(a, "G1", None, "2026-01-01")], [_mov(a, "G1", None, 10, "2026-01-01")])
    batches = [
        (
            [_capa(a, "G1", None, "2026-02-01")],
            [_mov(a, "G1", None, 10, "2026-01-01"), _mov(a, "G1", None, 11, "2026-02-01")],
        )
    ]
    canonical, deltas = _write_batches(tmp_path, existing, batches)

    _capa_path, mov_path, _n_capa, n_mov = compact_deltas(
        T, deltas_dir=deltas, canonical_dir=canonical
    )

    assert n_mov == 2
    assert sorted(r["codigo"] for r in read_parquet_rows(mov_path)) == [10, 11]
    # The old merge kept the stale copy as a duplicate.
    _ref_capas, ref_movs = _reference(existing, batches)
    assert len(ref_movs) == 3


def test_output_keeps_schema_and_identity_metadata(tmp_path: Path):
    a = "00000010220248220001"
    canonical, deltas = _write_batches(
        tmp_path,
        ([], []),
        [([_capa(a, "G1", 1, "2026-02-01")], [_mov(a, "G1", 1, 10, "2026-02-01")])],
    )
    capa_path, mov_path, _, _ = compact_deltas(T, deltas_dir=deltas, canonical_dir=canonical)
    for path, schema in ((capa_path, archive.CAPA_SCHEMA), (mov_path, archive.MOVIMENTOS_SCHEMA)):
        read = pq.read_schema(path)
        assert read.names == schema.names
        assert [str(f.type) for f in read] == [str(f.type) for f in schema]
        meta = {k.decode(): v.decode() for k, v in (read.metadata or {}).items()}
        assert meta["causaganha.item_id"] == archive.item_id(T)
        assert meta["causaganha.schema_version"] == archive.DATAJUD_SCHEMA_VERSION
