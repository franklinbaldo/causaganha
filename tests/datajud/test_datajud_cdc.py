"""Tests for datajud.cdc — Checkpoints, L1 delta batching, compaction, and CDC sync.

Zero real network. Fully reproducible using temporary directories.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from datajud.cdc import (
    CdcCheckpoint,
    DataJudCdcCheckpointStore,
    compact_deltas,
    read_parquet_rows,
    sync_tribunal_cdc,
    write_delta_batch,
)


if TYPE_CHECKING:
    from pathlib import Path


CNJ_1 = "00000010220248220001"
CNJ_2 = "00000020320248220002"


def _sample_source(
    cnj: str,
    grau: str = "G1",
    orgao_cod: int = 100,
    updated_at: str = "2026-03-01T10:00:00.000Z",
    n_movs: int = 1,
) -> dict:
    return {
        "numeroProcesso": cnj,
        "grau": grau,
        "tribunal": "TJRO",
        "classe": {"codigo": 7, "nome": "Procedimento Comum Cível"},
        "assuntos": [{"codigo": 10433, "nome": "Indenização por Dano Moral"}],
        "orgaoJulgador": {"codigo": orgao_cod, "nome": "1ª Vara Cível"},
        "dataHoraUltimaAtualizacao": updated_at,
        "movimentos": [
            {
                "codigo": 26,
                "nome": "Distribuição",
                "dataHora": "2026-02-01T10:00:00.000Z",
                "complementosTabelados": [],
            }
            for _ in range(n_movs)
        ],
    }


# ── Checkpoint Store Tests ───────────────────────────────────────────────


def test_checkpoint_store_lifecycle(tmp_path: Path):
    db_path = tmp_path / "checkpoints.sqlite"
    store = DataJudCdcCheckpointStore(db_path)

    # Initial get returns None
    assert store.get("tjro") is None

    # Upsert
    cp = CdcCheckpoint(
        tribunal="tjro",
        since_iso="2026-01-01T00:00:00.000Z",
        last_sort_key=[1772359200000, CNJ_1],
        last_updated_at="2026-01-01T12:00:00.000Z",
        total_documents=50,
        total_batches=1,
        last_run_at="2026-01-02T00:00:00.000Z",
        status="in_progress",
    )
    store.upsert(cp)

    loaded = store.get("TJRO")  # case-insensitive
    assert loaded is not None
    assert loaded.tribunal == "tjro"
    assert loaded.since_iso == "2026-01-01T00:00:00.000Z"
    assert loaded.last_sort_key == [1772359200000, CNJ_1]
    assert loaded.total_documents == 50
    assert loaded.total_batches == 1
    assert loaded.status == "in_progress"

    # Update
    loaded.total_documents = 150
    loaded.total_batches = 3
    loaded.status = "completed"
    store.upsert(loaded)

    reloaded = store.get("tjro")
    assert reloaded is not None
    assert reloaded.total_documents == 150
    assert reloaded.status == "completed"

    # Reset
    store.reset("tjro")
    assert store.get("tjro") is None


# ── Delta Batch Writing ──────────────────────────────────────────────────


def test_write_delta_batch(tmp_path: Path):
    deltas_dir = tmp_path / "deltas"
    doc1 = _sample_source(CNJ_1, updated_at="2026-03-01T10:00:00.000Z", n_movs=2)
    doc2 = _sample_source(CNJ_2, updated_at="2026-03-01T11:00:00.000Z", n_movs=1)

    capa_path, mov_path, n_capa, n_mov = write_delta_batch(
        [doc1, doc2], "tjro", part_seq=1, deltas_dir=deltas_dir
    )

    assert capa_path is not None and capa_path.exists()
    assert mov_path is not None and mov_path.exists()
    assert n_capa == 2
    assert n_mov == 3

    capa_rows = read_parquet_rows(capa_path)
    assert len(capa_rows) == 2
    assert {r["numero_processo"] for r in capa_rows} == {CNJ_1, CNJ_2}

    mov_rows = read_parquet_rows(mov_path)
    assert len(mov_rows) == 3


def test_write_delta_batch_empty_or_malformed(tmp_path: Path):
    deltas_dir = tmp_path / "deltas"
    capa_path, mov_path, n_capa, n_mov = write_delta_batch(
        [], "tjro", part_seq=1, deltas_dir=deltas_dir
    )
    assert capa_path is None
    assert n_capa == 0

    # Malformed doc missing required keys
    capa_p2, _, n_c2, _ = write_delta_batch(
        [{"bad": "data"}], "tjro", part_seq=2, deltas_dir=deltas_dir
    )
    assert capa_p2 is None
    assert n_c2 == 0


# ── Delta Compaction into Canonical L0 ───────────────────────────────────


def test_compact_deltas_merges_and_cleans(tmp_path: Path):
    deltas_dir = tmp_path / "deltas"
    canonical_dir = tmp_path / "canonical"

    # Batch 1: doc1 v1 and doc2
    doc1_v1 = _sample_source(CNJ_1, updated_at="2026-03-01T10:00:00.000Z", n_movs=1)
    doc2 = _sample_source(CNJ_2, updated_at="2026-03-01T11:00:00.000Z", n_movs=1)
    write_delta_batch([doc1_v1, doc2], "tjro", part_seq=1, deltas_dir=deltas_dir)

    # Batch 2: doc1 v2 (more recent, replaces v1 and adds a second movement)
    doc1_v2 = _sample_source(CNJ_1, updated_at="2026-03-01T12:00:00.000Z", n_movs=2)
    write_delta_batch([doc1_v2], "tjro", part_seq=2, deltas_dir=deltas_dir)

    capa_can, mov_can, n_capa, n_mov = compact_deltas(
        "tjro",
        deltas_dir=deltas_dir,
        canonical_dir=canonical_dir,
        clean_after_compact=True,
    )

    assert capa_can.exists()
    assert mov_can.exists()
    assert n_capa == 2  # CNJ_1 and CNJ_2 (doc1_v2 replaced doc1_v1)
    assert n_mov == 3  # 2 movements from doc1_v2 + 1 movement from doc2

    capa_rows = read_parquet_rows(capa_can)
    cnj1_row = next(r for r in capa_rows if r["numero_processo"] == CNJ_1)
    assert cnj1_row["ultima_atualizacao"] == "2026-03-01T12:00:00.000Z"
    assert cnj1_row["n_movimentos"] == 2

    # Verify deltas were cleaned up
    remaining_deltas = list((deltas_dir / "tjro").glob("*.parquet"))
    assert not remaining_deltas


# ── CDC Sync Orchestration ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sync_tribunal_cdc_full_flow(tmp_path: Path):
    base_dir = tmp_path / "cdc"
    canonical_dir = tmp_path / "canonical"

    doc1 = _sample_source(CNJ_1, updated_at="2026-03-01T10:00:00.000Z")
    doc2 = _sample_source(CNJ_2, updated_at="2026-03-01T11:00:00.000Z")

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    async def mock_iter(**_kwargs):
        yield [doc1], [1, CNJ_1]
        yield [doc2], [2, CNJ_2]

    mock_client.iter_updated_since = mock_iter

    res = await sync_tribunal_cdc(
        "tjro",
        since_iso="2026-03-01T00:00:00.000Z",
        base_dir=base_dir,
        canonical_dir=canonical_dir,
        consolidate=True,
        client=mock_client,
    )

    assert res.tribunal == "tjro"
    assert res.documents_streamed == 2
    assert res.batches_streamed == 2
    assert res.consolidated_capas == 2
    assert res.consolidated_movs == 2
    assert res.checkpoint.status == "completed"
    assert res.checkpoint.total_documents == 2
    assert res.checkpoint.last_sort_key == [2, CNJ_2]

    # Verify store recorded completion
    store = DataJudCdcCheckpointStore(base_dir / "checkpoints.sqlite")
    saved_cp = store.get("tjro")
    assert saved_cp is not None
    assert saved_cp.status == "completed"
    assert saved_cp.total_documents == 2


# ── CLI End-to-End Test ──────────────────────────────────────────────────


def test_cli_cdc_command(tmp_path: Path, monkeypatch):
    import contextlib
    import io
    from datajud.__main__ import app

    base_dir = tmp_path / "cdc"
    canonical_dir = tmp_path / "canonical"

    mock_result = MagicMock()
    mock_result.documents_streamed = 10
    mock_result.batches_streamed = 1
    mock_result.consolidated_capas = 10
    mock_result.consolidated_movs = 15
    mock_result.checkpoint = MagicMock(
        total_documents=10,
        last_updated_at="2026-03-01T12:00:00.000Z",
        status="completed",
    )

    async def fake_sync(*args, **kwargs):
        return mock_result

    monkeypatch.setattr("datajud.cdc.sync_tribunal_cdc", fake_sync)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        exit_code = app(
            [
                "cdc",
                "--tribunal",
                "tjro",
                "--since",
                "2026-03-01T00:00:00.000Z",
                "--page-size",
                "10",
                "--data-dir",
                str(base_dir),
                "--canonical-dir",
                str(canonical_dir),
            ],
            exit_on_error=False,
            result_action="return_value",
        )

    output = buf.getvalue()
    assert exit_code == 0
    assert "DataJud CDC — Tribunal: TJRO" in output
    assert "Sincronização CDC concluída" in output
    assert "Documentos nesta sessão: 10" in output
    assert "Total de capas        : 10" in output
