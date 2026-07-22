"""Behavior tests for causaganha_mcp status tools (RFC 0013 Fase 3A, RFC 0014 M1).

Calls each tool's underlying function directly (`tool.fn(...)`) against a
manifest fixture built with the same package's own manifest API — no
FastMCP transport involved, since the transport isn't what these tools do
differently from the CLI's own `status` commands; the mapping from
manifest state to a small, structured, credential-free result is.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from causaganha_mcp.server import build_server
from datajud.manifest import STATUS_OK, ManifestDataJud
from djen_backup.manifest import HEADER, SyncManifest
from stj_acordaos.manifest import ManifestSTJ
from tjro_juris.manifest import ManifestJuris, ManifestJurisEntry


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def mcp():
    return build_server()


async def _tool_fn(mcp, name: str):
    tool = await mcp.get_tool(name)
    return tool.fn


# ── datajud_status ──────────────────────────────────────────────────────


async def test_datajud_status_empty_manifest(mcp, tmp_path: Path) -> None:
    fn = await _tool_fn(mcp, "datajud_status")
    result = fn(data_dir=str(tmp_path / "datajud"))
    assert result.encontrado is False
    assert result.total == 0
    assert result.ultima_atualizacao is None
    assert result.fonte == "manifest_local"
    assert result.canonica is True


async def test_datajud_status_populated_manifest(mcp, tmp_path: Path) -> None:
    data_dir = tmp_path / "datajud"
    data_dir.mkdir()
    manifest = ManifestDataJud.load_local(data_dir / "datajud-manifest.csv")
    manifest.upsert("00000010220248220001", "tjro", docs=2, status=STATUS_OK)
    manifest.upsert("00000020320248220002", "tjro", docs=0, status=STATUS_OK)
    manifest.upsert("00000030420248220003", "tjro", docs=0, status="erro")
    manifest.save_local(data_dir / "datajud-manifest.csv")

    fn = await _tool_fn(mcp, "datajud_status")
    result = fn(data_dir=str(data_dir))

    assert result.encontrado is True
    assert result.total == 3
    assert result.ok == 2
    assert result.com_docs == 1
    assert result.sem_docs == 1
    assert result.com_erro == 1
    assert result.ultima_atualizacao is not None


# ── tjro_juris_status ───────────────────────────────────────────────────


async def test_tjro_juris_status_empty_manifest(mcp, tmp_path: Path) -> None:
    fn = await _tool_fn(mcp, "tjro_juris_status")
    result = fn(data_dir=str(tmp_path / "tjro-juris"))
    assert result.encontrado is False
    assert result.total == 0
    assert result.enviados == 0
    assert result.pendentes == 0
    assert result.ultima_atualizacao is None


async def test_tjro_juris_status_populated_manifest(mcp, tmp_path: Path) -> None:
    data_dir = tmp_path / "tjro-juris"
    data_dir.mkdir()
    manifest = ManifestJuris()
    manifest.upsert(
        ManifestJurisEntry(tipo="ACÓRDÃO", mes_ano="2026-06", ia_status="uploaded", n_docs=5)
    )
    manifest.upsert(ManifestJurisEntry(tipo="ACÓRDÃO", mes_ano="2026-07", ia_status="", n_docs=3))
    manifest.save_local(data_dir / "tjro-juris-manifest.csv")

    fn = await _tool_fn(mcp, "tjro_juris_status")
    result = fn(data_dir=str(data_dir))

    assert result.encontrado is True
    assert result.total == 2
    assert result.enviados == 1
    assert result.pendentes == 1
    assert result.ultima_atualizacao is not None


# ── stj_acordaos_status ─────────────────────────────────────────────────


async def test_stj_acordaos_status_empty_manifest(mcp, tmp_path: Path) -> None:
    fn = await _tool_fn(mcp, "stj_acordaos_status")
    result = fn(manifest_path=str(tmp_path / "stj-manifest.csv"))
    assert result.encontrado is False
    assert result.total == 0
    assert result.enviados == 0
    assert result.pendentes == 0
    assert result.ultima_atualizacao is None


async def test_stj_acordaos_status_populated_manifest(mcp, tmp_path: Path) -> None:
    manifest_path = tmp_path / "stj-manifest.csv"
    manifest = ManifestSTJ(manifest_path)
    manifest.upsert("20260531.json.json", "json", "2026-05-31", "uploaded", 12)
    manifest.upsert("20260630.json.json", "json", "2026-06-30", "", 0)
    manifest.save()

    fn = await _tool_fn(mcp, "stj_acordaos_status")
    result = fn(manifest_path=str(manifest_path))

    assert result.encontrado is True
    assert result.total == 2
    assert result.enviados == 1
    assert result.pendentes == 1
    assert result.ultima_atualizacao is not None


# ── djen_backup_status ──────────────────────────────────────────────────


async def test_djen_backup_status_empty_manifest(mcp, tmp_path: Path) -> None:
    fn = await _tool_fn(mcp, "djen_backup_status")
    result = fn(manifest_file=str(tmp_path / "sync-manifest.csv"))
    assert result.encontrado is False
    assert result.total == 0
    assert result.enviados == 0
    assert result.disponiveis == 0
    assert result.ausentes == 0
    assert result.desconhecidos == 0
    assert result.ultima_atualizacao is None
    assert result.fonte == "cache_local"
    assert result.canonica is False
    assert result.aviso is not None


async def test_djen_backup_status_populated_manifest(mcp, tmp_path: Path) -> None:
    manifest_file = tmp_path / "sync-manifest.csv"
    manifest_file.write_text(
        f"{HEADER}\n"
        "TJRO,2026-01-01,uploaded,available,200,2026-01-01T00:00:00\n"
        "TJRO,2026-01-02,,available,200,2026-01-02T00:00:00\n"
        "TJRO,2026-01-03,,absent,404,2026-01-03T00:00:00\n"
        "TJRO,2026-01-04,,,,\n",
        encoding="utf-8",
    )
    # Sanity: confirm the fixture round-trips through the manifest's own
    # loader the same way the tool does, before trusting the tool's counts.
    manifest = SyncManifest()
    assert manifest.load_from_disk(manifest_file) == 4

    fn = await _tool_fn(mcp, "djen_backup_status")
    result = fn(manifest_file=str(manifest_file))

    assert result.encontrado is True
    assert result.total == 4
    assert result.enviados == 1
    assert result.disponiveis == 1
    assert result.ausentes == 1
    assert result.desconhecidos == 1
    assert result.ultima_atualizacao == "2026-01-03T00:00:00"
    assert result.fonte == "cache_local"
    assert result.canonica is False
    assert result.aviso is not None
