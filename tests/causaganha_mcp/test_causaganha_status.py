"""Behavior tests for ``causaganha_status`` (RFC 0014 M1).

Three specific guarantees from RFC 0014 §3, each with its own test:
service-layer reuse (never the sibling tools via the MCP protocol), no
health verdict (facts only), and a missing manifest producing a partial
result per-pipeline rather than failing the whole call.
"""

from __future__ import annotations

import inspect

import pytest

import causaganha_mcp.tools.status as status_module
from causaganha_mcp.server import build_server
from datajud.manifest import STATUS_OK, ManifestDataJud


@pytest.fixture
def mcp():
    return build_server()


async def _status_fn(mcp):
    tool = await mcp.get_tool("causaganha_status")
    return tool.fn


async def test_all_four_pipelines_appear_even_with_no_local_data(mcp, tmp_path, monkeypatch):
    # Redirect every pipeline's default path into an empty tmp_path so this
    # test doesn't depend on (or pollute) the repo's real data/ directory.
    monkeypatch.chdir(tmp_path)

    fn = await _status_fn(mcp)
    result = fn()

    names = [p.nome for p in result.pipelines]
    assert names == ["djen", "tjro_juris", "stj_acordaos", "datajud"]
    for pipeline in result.pipelines:
        assert pipeline.encontrado is False
        assert pipeline.total == 0
        assert pipeline.ultima_atualizacao is None
    # DJEN alone is a local cache of a canonical remote source.
    djen = result.pipelines[0]
    assert djen.fonte == "cache_local"
    assert djen.canonica is False
    assert djen.aviso is not None
    for pipeline in result.pipelines[1:]:
        assert pipeline.fonte == "manifest_local"
        assert pipeline.canonica is True


async def test_datajud_pipeline_reflects_a_populated_manifest(mcp, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data" / "datajud"
    data_dir.mkdir(parents=True)
    manifest = ManifestDataJud.load_local(data_dir / "datajud-manifest.csv")
    manifest.upsert("00000010220248220001", "tjro", docs=2, status=STATUS_OK)
    manifest.save_local(data_dir / "datajud-manifest.csv")

    fn = await _status_fn(mcp)
    result = fn()

    datajud_entry = next(p for p in result.pipelines if p.nome == "datajud")
    assert datajud_entry.encontrado is True
    assert datajud_entry.total == 1
    assert datajud_entry.contagens == {"ok": 1, "com_docs": 1, "sem_docs": 0, "com_erro": 0}
    assert datajud_entry.ultima_atualizacao is not None


async def test_no_health_verdict_field_anywhere_in_the_schema(mcp) -> None:
    """RFC 0014 §3: facts only — no invented 'saudável'/'degradado' field."""
    tool = await mcp.get_tool("causaganha_status")
    schema_text = str(tool.output_schema)
    for banned in ("saudavel", "saúde", "health", "degradado", "status_geral"):
        assert banned not in schema_text.lower()


def test_reuses_service_layer_directly_not_the_other_tools_via_mcp() -> None:
    """RFC 0014 §3: call service.py directly, never the sibling tools via MCP.

    A source-level guard, not a behavioral one — the point is that
    `tools/status.py` must not import the other `causaganha_mcp.tools.*`
    modules or reach for `get_tool`/`call_tool`/a `fastmcp.Client`, which
    would mean routing an in-process call through the MCP protocol just to
    build a response the protocol is about to serve again.
    """
    source = inspect.getsource(status_module)
    assert "causaganha_mcp.tools" not in source
    assert "get_tool" not in source
    assert "call_tool" not in source
    assert "Client(" not in source
    # Positive check: it does import every package's plain service module.
    for module in (
        "datajud.service",
        "djen_backup.service",
        "stj_acordaos.service",
        "tjro_juris.service",
    ):
        assert module in source


async def test_one_pipeline_erroring_does_not_fail_the_whole_call(mcp, tmp_path, monkeypatch):
    """RFC 0014 §3: a broken manifest on one pipeline yields a partial result, not a crash."""
    monkeypatch.chdir(tmp_path)

    # A directory where djen's manifest file is expected raises OSError
    # (IsADirectoryError, a subclass) on the read — a stand-in for "local
    # disk is unhappy" without needing to actually corrupt a real file.
    from djen_backup import service as djen_backup_service

    broken_path = tmp_path / "data" / "sync-manifest.csv"
    broken_path.mkdir(parents=True)
    monkeypatch.setattr(djen_backup_service, "DEFAULT_MANIFEST_FILE", broken_path)

    fn = await _status_fn(mcp)
    result = fn()  # must not raise

    djen_entry = next(p for p in result.pipelines if p.nome == "djen")
    assert djen_entry.encontrado is False
    assert djen_entry.aviso is not None
    # The other three pipelines are unaffected.
    assert len(result.pipelines) == 4


async def test_a_genuinely_malformed_manifest_also_yields_a_partial_result(
    mcp, tmp_path, monkeypatch
):
    """RFC 0014 review: OSError alone doesn't cover a malformed (parseable-as-file,
    unparseable-as-manifest) CSV — `ManifestJuris.load_local` raises `ManifestFormatError`
    (KeyError/ValueError translated at the parsing boundary) for a row missing the
    `tipo` column, which must be caught the same way as an I/O failure.
    """
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data" / "tjro-juris"
    data_dir.mkdir(parents=True)
    (data_dir / "tjro-juris-manifest.csv").write_text(
        "mes_ano,ia_status,n_docs,updated_at\n2024-01,uploaded,10,\n", encoding="utf-8"
    )

    fn = await _status_fn(mcp)
    result = fn()  # must not raise

    tjro_juris_entry = next(p for p in result.pipelines if p.nome == "tjro_juris")
    assert tjro_juris_entry.encontrado is False
    assert tjro_juris_entry.aviso is not None
    # The other three pipelines are unaffected.
    assert len(result.pipelines) == 4
    assert {p.nome for p in result.pipelines} == {"djen", "tjro_juris", "stj_acordaos", "datajud"}
