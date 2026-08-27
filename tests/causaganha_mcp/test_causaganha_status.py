"""Behavior tests for ``causaganha_status`` (RFC 0014 M1 + health foundation #892).

The aggregate stays factual: no global health verdict is invented. Each pipeline
reports whether its concrete source was present, absent, or unavailable, and a
failure in one source must not hide the other pipelines.
"""

from __future__ import annotations

import inspect
from datetime import date
from unittest.mock import Mock

import httpx
import pytest

import causaganha_mcp.tools.status as status_module
from causaganha_mcp.server import build_server
from datajud import state as datajud_state
from datajud.manifest import STATUS_OK, ManifestDataJud
from djen_backup.manifest import SyncManifest


@pytest.fixture
def mcp():
    return build_server()


@pytest.fixture(autouse=True)
def _default_remote_sources_absent(monkeypatch):
    monkeypatch.setattr(
        status_module.djen_published,
        "read_published_manifest_observation",
        lambda: None,
    )
    monkeypatch.setattr(
        status_module.datajud_state,
        "read_remote_state",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(status_module.tjro_juris_archive, "read_manifest_text", lambda: None)
    monkeypatch.setattr(status_module.stj_acordaos_archive, "read_manifest_text", lambda: None)


async def _status_fn(mcp):
    tool = await mcp.get_tool("causaganha_status")
    return tool.fn


async def test_all_four_pipelines_appear_even_with_no_state(mcp, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    fn = await _status_fn(mcp)
    result = fn()

    names = [p.nome for p in result.pipelines]
    assert names == ["djen", "tjro_juris", "stj_acordaos", "datajud"]
    for pipeline in result.pipelines:
        assert pipeline.encontrado is False
        assert pipeline.total == 0
        assert pipeline.ultima_atualizacao is None
        assert pipeline.observacao == "absent"

    djen, tjro, stj, datajud = result.pipelines
    assert djen.fonte == "manifest_publicado"
    assert djen.canonica is True
    assert tjro.fonte == "manifest_publicado"
    assert stj.fonte == "manifest_publicado"
    assert datajud.fonte == "bundle_publicado"
    assert tjro.canonica is True
    assert stj.canonica is True
    assert datajud.canonica is True


async def test_djen_reflects_published_materialization(mcp, monkeypatch):
    manifest = SyncManifest()
    manifest.apply_event(
        "TJRO",
        date(2026, 8, 22),
        ia_status="uploaded",
        updated_at="2026-08-23T12:00:00+00:00",
    )
    manifest.apply_event(
        "TJRO",
        date(2026, 8, 25),
        djen_status="available",
        djen_raw="200",
        updated_at="2026-08-25T08:00:00+00:00",
    )
    publication = "2026-08-25T09:00:00+00:00"
    observation = status_module.djen_published.PublishedManifestObservation(
        manifest=manifest,
        components=(
            status_module.djen_published.PublishedComponent(
                name=status_module.djen_published.IA_PARQUET_FILENAME,
                modified_at=publication,
            ),
        ),
    )
    monkeypatch.setattr(
        status_module.djen_published,
        "read_published_manifest_observation",
        lambda: observation,
    )

    fn = await _status_fn(mcp)
    result = fn()

    djen = result.pipelines[0]
    assert djen.observacao == "present"
    assert djen.encontrado is True
    assert djen.total == 2
    assert djen.contagens == {
        "enviados": 1,
        "disponiveis": 1,
        "ausentes": 0,
        "desconhecidos": 0,
    }
    assert djen.ultima_atualizacao == "2026-08-25T08:00:00+00:00"
    assert djen.fonte == "manifest_publicado"
    assert djen.canonica is True
    assert djen.publicacao_observacao == "present"
    assert djen.ultima_publicacao == publication


async def test_djen_published_failure_is_unavailable_not_empty_and_keeps_partial_result(
    mcp, monkeypatch
):
    error = status_module.djen_published.PublishedManifestUnavailable("archive unavailable")
    monkeypatch.setattr(
        status_module.djen_published,
        "read_published_manifest_observation",
        Mock(side_effect=error),
    )

    fn = await _status_fn(mcp)
    result = fn()

    djen = result.pipelines[0]
    assert djen.observacao == "unavailable"
    assert djen.encontrado is False
    assert djen.total == 0
    assert djen.fonte == "manifest_publicado"
    assert djen.canonica is True
    assert "não significa dataset vazio" in djen.aviso.lower()
    assert len(result.pipelines) == 4


async def test_tjro_and_stj_reflect_published_manifests(mcp, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        status_module.tjro_juris_archive,
        "read_manifest_text",
        lambda: (
            "tipo,mes_ano,ia_status,n_docs,updated_at\n"
            "ACORDAO,2026-07,uploaded,12,2026-08-23T10:00:00+00:00\n"
            "DECISAO,2026-08,,4,2026-08-23T12:00:00+00:00\n"
        ),
    )
    monkeypatch.setattr(
        status_module.stj_acordaos_archive,
        "read_manifest_text",
        lambda: (
            "arquivo,tipo,data_extracao,ia_status,n_registros,updated_at\n"
            "a.zip,zip,2026-08-22,uploaded,10,2026-08-23T09:00:00+00:00\n"
            "b.json,json,2026-08-23,,5,2026-08-23T13:00:00+00:00\n"
        ),
    )

    fn = await _status_fn(mcp)
    result = fn()

    tjro = next(p for p in result.pipelines if p.nome == "tjro_juris")
    assert tjro.observacao == "present"
    assert tjro.encontrado is True
    assert tjro.total == 2
    assert tjro.contagens == {"enviados": 1, "pendentes": 1}
    assert tjro.ultima_atualizacao == "2026-08-23T12:00:00+00:00"
    assert tjro.fonte == "manifest_publicado"
    assert tjro.canonica is True

    stj = next(p for p in result.pipelines if p.nome == "stj_acordaos")
    assert stj.observacao == "present"
    assert stj.encontrado is True
    assert stj.total == 2
    assert stj.contagens == {"enviados": 1, "pendentes": 1}
    assert stj.ultima_atualizacao == "2026-08-23T13:00:00+00:00"
    assert stj.fonte == "manifest_publicado"
    assert stj.canonica is True


@pytest.mark.parametrize("pipeline", ["tjro", "stj"])
async def test_published_manifest_transport_failure_is_unavailable_not_empty(
    pipeline, mcp, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    error = httpx.ConnectError("archive unavailable")
    target = (
        status_module.tjro_juris_archive
        if pipeline == "tjro"
        else status_module.stj_acordaos_archive
    )
    monkeypatch.setattr(target, "read_manifest_text", Mock(side_effect=error))

    fn = await _status_fn(mcp)
    result = fn()

    name = "tjro_juris" if pipeline == "tjro" else "stj_acordaos"
    entry = next(p for p in result.pipelines if p.nome == name)
    assert entry.observacao == "unavailable"
    assert entry.encontrado is False
    assert entry.total == 0
    assert entry.fonte == "manifest_publicado"
    assert entry.canonica is True
    assert "não significa dataset vazio" in entry.aviso.lower()
    assert len(result.pipelines) == 4


@pytest.mark.parametrize("pipeline", ["tjro", "stj"])
async def test_malformed_published_manifest_is_unavailable(pipeline, mcp, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = (
        status_module.tjro_juris_archive
        if pipeline == "tjro"
        else status_module.stj_acordaos_archive
    )
    monkeypatch.setattr(target, "read_manifest_text", lambda: "wrong,columns\n1,2\n")

    fn = await _status_fn(mcp)
    result = fn()

    name = "tjro_juris" if pipeline == "tjro" else "stj_acordaos"
    entry = next(p for p in result.pipelines if p.nome == name)
    assert entry.observacao == "unavailable"
    assert entry.encontrado is False
    assert entry.total == 0
    assert entry.fonte == "manifest_publicado"
    assert "inválido" in entry.aviso.lower()
    assert len(result.pipelines) == 4


async def test_datajud_pipeline_reflects_the_verified_published_generation(
    mcp, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    manifest_path = tmp_path / "manifest.csv"
    manifest = ManifestDataJud.load_local(manifest_path)
    manifest.upsert("00000010220248220001", "tjro", docs=2, status=STATUS_OK)
    manifest.save_local(manifest_path)

    published = datajud_state.PublishedState(
        tribunal="tjro",
        generation="generation-123",
        manifest_text=manifest_path.read_text(encoding="utf-8"),
        published_at="2026-08-23T12:00:00+00:00",
        files={},
    )
    monkeypatch.setattr(
        status_module.datajud_state,
        "read_remote_state",
        lambda *_args, **_kwargs: published,
    )

    fn = await _status_fn(mcp)
    result = fn()

    datajud_entry = next(p for p in result.pipelines if p.nome == "datajud")
    assert datajud_entry.observacao == "present"
    assert datajud_entry.encontrado is True
    assert datajud_entry.total == 1
    assert datajud_entry.contagens == {"ok": 1, "com_docs": 1, "sem_docs": 0, "com_erro": 0}
    assert datajud_entry.ultima_atualizacao is not None
    assert datajud_entry.publicado_em == "2026-08-23T12:00:00+00:00"
    assert datajud_entry.geracao == "generation-123"
    assert datajud_entry.fonte == "bundle_publicado"
    assert datajud_entry.canonica is True


async def test_datajud_remote_failure_is_unavailable_not_empty_and_keeps_partial_result(
    mcp, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    remote_error = datajud_state.RemoteStateError("archive unavailable")
    monkeypatch.setattr(
        status_module.datajud_state,
        "read_remote_state",
        Mock(side_effect=remote_error),
    )

    fn = await _status_fn(mcp)
    result = fn()

    datajud_entry = next(p for p in result.pipelines if p.nome == "datajud")
    assert datajud_entry.observacao == "unavailable"
    assert datajud_entry.encontrado is False
    assert datajud_entry.total == 0
    assert datajud_entry.fonte == "bundle_publicado"
    assert datajud_entry.canonica is True
    assert "não significa dataset vazio" in datajud_entry.aviso.lower()
    assert len(result.pipelines) == 4


async def test_no_health_verdict_field_anywhere_in_the_schema(mcp) -> None:
    tool = await mcp.get_tool("causaganha_status")
    schema_text = str(tool.output_schema)
    for banned in ("saudavel", "saúde", "health", "degradado", "status_geral"):
        assert banned not in schema_text.lower()


def test_reuses_authorities_directly_not_the_other_tools_via_mcp() -> None:
    source = inspect.getsource(status_module)
    assert "causaganha_mcp.tools" not in source
    assert "get_tool" not in source
    assert "call_tool" not in source
    assert "Client(" not in source
    for module in (
        "datajud_state",
        "djen_published",
        "stj_acordaos_archive",
        "tjro_juris_archive",
    ):
        assert module in source
