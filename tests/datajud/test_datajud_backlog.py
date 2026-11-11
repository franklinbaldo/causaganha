"""Tests for datajud.backlog — Time-boxed slices, SQLite backlog store, and orchestration.

Zero real network.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from datajud.backlog import (
    DataJudBacklogStore,
    run_backlog,
    run_backlog_slice,
)


if TYPE_CHECKING:
    from pathlib import Path


CNJ_1 = "00000010220248220001"


# ── Backlog Store Tests ───────────────────────────────────────────────────


def test_backlog_store_init_and_pending_selection(tmp_path: Path):
    db_file = tmp_path / "backlog_slices.sqlite"
    store = DataJudBacklogStore(db_file)

    # Initialize 2 years: 2024 and 2025 (24 monthly slices)
    slices = store.init_slices("tjro", 2024, 2025, slice_by="month")
    assert len(slices) == 24

    # The next pending slice should be the newest: 2025-12
    pending = store.get_next_pending_slice("tjro")
    assert pending is not None
    assert pending.ano == 2025
    assert pending.mes == 12
    assert pending.status == "pending"

    # Mark 2025-12 as completed
    pending.status = "completed"
    pending.documentos_coletados = 500
    store.update_slice(pending)

    # Next pending should now be 2025-11
    next_pending = store.get_next_pending_slice("tjro")
    assert next_pending is not None
    assert next_pending.ano == 2025
    assert next_pending.mes == 11


def test_backlog_store_yearly_slices(tmp_path: Path):
    db_file = tmp_path / "backlog_yearly.sqlite"
    store = DataJudBacklogStore(db_file)

    slices = store.init_slices("tjro", 2020, 2023, slice_by="year")
    assert len(slices) == 4
    assert {s.ano for s in slices} == {2020, 2021, 2022, 2023}
    assert all(s.mes == 0 for s in slices)


# ── Run Backlog Slice & Orchestrator Tests ─────────────────────────────────


@pytest.mark.asyncio
async def test_run_backlog_slice_execution(tmp_path: Path):
    db_file = tmp_path / "backlog.sqlite"
    store = DataJudBacklogStore(db_file)
    store.init_slices("tjro", 2025, 2025, slice_by="month")

    slice_item = store.get_slice("tjro", 2025, 1)
    assert slice_item is not None

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    sample_doc = {
        "numeroProcesso": CNJ_1,
        "grau": "G1",
        "dataHoraUltimaAtualizacao": "2025-01-15T10:00:00.000Z",
        "dataAjuizamento": "20250110120000",
    }

    async def mock_iter(**_kwargs):
        yield [sample_doc], ["sort_val", CNJ_1]

    mock_client.iter_updated_since = mock_iter

    docs, batches = await run_backlog_slice(
        slice_item,
        store,
        base_dir=tmp_path / "cdc",
        daily_dir=tmp_path / "daily",
        index_dir=tmp_path / "index",
        client=mock_client,
    )

    assert docs == 1
    assert batches == 1

    # Reload slice from store
    reloaded = store.get_slice("tjro", 2025, 1)
    assert reloaded is not None
    assert reloaded.status == "completed"
    assert reloaded.documentos_coletados == 1
    assert reloaded.search_after_cursor == ["sort_val", CNJ_1]


@pytest.mark.asyncio
async def test_run_backlog_orchestrator_max_slices(tmp_path: Path):
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    async def mock_iter(**_kwargs):
        yield [], None

    mock_client.iter_updated_since = mock_iter

    res = await run_backlog(
        "tjro",
        2024,
        2024,
        slice_by="month",
        max_slices=2,
        consolidate=False,
        base_dir=tmp_path / "backlog",
        client=mock_client,
    )

    assert res["tribunal"] == "tjro"
    assert res["slices_processed"] == 2


# ── CLI End-to-End Test ──────────────────────────────────────────────────


def test_cli_backlog_command(tmp_path: Path, monkeypatch):
    import contextlib
    import io
    from datajud.__main__ import app

    base_dir = tmp_path / "backlog"

    async def fake_run_backlog(*args, **kwargs):
        return {
            "tribunal": "tjro",
            "slices_processed": 3,
            "total_documents": 250,
            "uploaded_files": [],
        }

    monkeypatch.setattr("datajud.backlog.run_backlog", fake_run_backlog)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        exit_code = app(
            [
                "backlog",
                "--tribunal",
                "tjro",
                "--start-year",
                "2024",
                "--end-year",
                "2025",
                "--max-slices",
                "3",
                "--data-dir",
                str(base_dir),
            ],
            exit_on_error=False,
            result_action="return_value",
        )

    output = buf.getvalue()
    assert exit_code == 0
    assert "DataJud Backlog — Tribunal: TJRO" in output
    assert "Fatias processadas nesta sessão: 3" in output
    assert "Documentos coletados           : 250" in output
