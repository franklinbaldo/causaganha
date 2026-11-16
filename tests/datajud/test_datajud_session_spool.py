"""On-disk session spool and DuckDB index merge (#1708)."""

from __future__ import annotations

import zipfile
from typing import TYPE_CHECKING

import pyarrow.parquet as pq

from datajud.daily_pack import SessionSpool, pack_daily_zip, update_resolution_index


if TYPE_CHECKING:
    from pathlib import Path


A = "00000010220248220001"
B = "00000020320248220002"


def _doc(cnj: str, upd: str, grau: str = "G1", extra: str = "") -> dict:
    return {"numeroProcesso": cnj, "grau": grau, "dataHoraUltimaAtualizacao": upd, "x": extra}


def _entries(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as zf:
        return {name: zf.read(name) for name in zf.namelist()}


def test_spool_zip_matches_in_memory_packer(tmp_path: Path):
    docs = [
        _doc(A, "2026-01-01", extra="old"),
        _doc(B, "2026-01-02"),
        _doc(A, "2026-01-03", extra="new"),
        _doc(A, "2026-01-03", extra="tie-later-wins"),
        _doc(B, "2026-01-01", extra="older-ignored"),
    ]
    spool = SessionSpool(tmp_path / "s.ndjson")
    spool.add(docs[:2])
    spool.add(docs[2:])
    spool.close()

    spooled, n_spooled = spool.pack_zip("tjro", "d1", tmp_path / "spool")
    reference, n_ref = pack_daily_zip(docs, "tjro", "d1", tmp_path / "ref")

    assert n_spooled == n_ref == 2
    assert _entries(spooled) == _entries(reference)


def test_spool_keeps_only_pointers_in_memory(tmp_path: Path):
    spool = SessionSpool(tmp_path / "s.ndjson")
    spool.add([_doc(A, "2026-01-01", extra="x" * 10_000)])
    pointer = next(iter(spool._pointers.values()))  # noqa: SLF001 — asserting the representation
    assert all(not isinstance(part, dict) for part in pointer)
    assert len(spool) == 1
    assert spool.index_documents() == [
        {"numeroProcesso": A, "grau": "G1", "dataHoraUltimaAtualizacao": "2026-01-01"}
    ]


def test_index_merge_latest_wins_and_ties_go_to_new(tmp_path: Path):
    index = tmp_path / "idx.parquet"
    update_resolution_index(index, [_doc(A, "2026-01-02"), _doc(B, "2026-01-05")], "z1.zip", "tjro")
    total = update_resolution_index(
        index,
        [_doc(A, "2026-01-02"), _doc(B, "2026-01-01")],  # A ties -> new; B older -> kept
        "z2.zip",
        "tjro",
    )
    rows = {r["numero_processo"]: r for r in pq.read_table(index).to_pylist()}
    assert total == 2
    assert rows[A]["zip_file"] == "z2.zip"
    assert rows[B]["zip_file"] == "z1.zip"
    assert list(rows) == sorted(rows)
