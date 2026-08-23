"""Behavior tests for ``causaganha_status`` (RFC 0014 M1 + health foundation #892).

The aggregate stays factual: no global health verdict is invented. Each pipeline
reports whether its concrete source was present, absent, or unavailable, and a
failure in one source must not hide the other pipelines.
"""

from __future__ import annotations

import inspect
from unittest.mock import Mock

import pytest

import causaganha_mcp.tools.status as status_module
from causaganha_mcp.server import build_server
from datajud import state as datajud_state
from datajud.manifest import STATUS_OK, ManifestDataJud


@pytest.fixture
def mcp():
    return build_server()


@pytest.fixture(autouse=True)
def _default_datajud_remote_absent(monkeypatch):
    monkeypatch.setattr(
        status_module.datajud_state,
        "read_remote_state",
        lambda *_args, **_kwargs: None,
    )


async def _status_fn(mcp):
    tool = await mcp.get_tool("causaganha_status")
    return tool.fn


async def test_all_four_pipelines_appear_even_with_no_local_data(mcp, tmp_path, monkeypatch):
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

    djen = result.pipelines[0]
    assert djen.fonte == "cache_local"
    assert djen.canonica is False
    assert djen.aviso is not None

    tjro, stj, datajud = result.pipelines[1:]
    assert tjro.fonte == "manifest_local"
    assert stj.fonte == "manifest_local"
    assert datajud.fonte == "bundle_publicado"
    assert datajud.canonica is True


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
    """#892 foundation remains factual until freshness policy is explicitly frozen."""
    tool = await mcp.get_tool("causaganha_status")
    schema_text = str(tool.output_schema)
    for banned in ("saudavel", "saúde", "health", "degradado", "status_geral"):
        assert banned not in schema_text.lower()


def test_reuses_authorities_directly_not_the_other_tools_via_mcp() -> None:
    """Build the aggregate in-process, never by recursively calling sibling MCP tools."""
    source = inspect.getsource(status_module)
    assert "causaganha_mcp.tools" not in source
    assert "get_tool" not in source
    assert "call_tool" not in source
    assert "Client(" not in source
    for module in (
        "datajud_state",
        "djen_backup.service",
        "stj_acordaos.service",
        "tjro_juris.service",
    ):
        assert module in source


async def test_one_pipeline_erroring_does_not_fail_the_whole_call(mcp, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    from djen_backup import service as djen_backup_service

    broken_path = tmp_path / "data" / "sync-manifest.csv"
    broken_path.mkdir(parents=True)
    monkeypatch.setattr(djen_backup_service, "DEFAULT_MANIFEST_FILE", broken_path)

    fn = await _status_fn(mcp)
    result = fn()

    djen_entry = next(p for p in result.pipelines if p.nome == "djen")
    assert djen_entry.observacao == "unavailable"
    assert djen_entry.encontrado is False
    assert djen_entry.aviso is not None
    assert len(result.pipelines) == 4


async def test_a_genuinely_malformed_manifest_also_yields_a_partial_result(
    mcp, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data" / "tjro-juris"
    data_dir.mkdir(parents=True)
    (data_dir / "tjro-juris-manifest.csv").write_text(
        "mes_ano,ia_status,n_docs,updated_at\n2024-01,uploaded,10,\n", encoding="utf-8"
    )

    fn = await _status_fn(mcp)
    result = fn()

    tjro_juris_entry = next(p for p in result.pipelines if p.nome == "tjro_juris")
    assert tjro_juris_entry.observacao == "unavailable"
    assert tjro_juris_entry.encontrado is False
    assert tjro_juris_entry.aviso is not None
    assert len(result.pipelines) == 4
    assert {p.nome for p in result.pipelines} == {"djen", "tjro_juris", "stj_acordaos", "datajud"}
