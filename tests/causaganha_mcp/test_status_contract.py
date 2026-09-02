"""Contract test for #892's consolidation slice.

Each pipeline observes its own authority through a different mechanism (a
composite parquet+segments reader for DJEN, an IA object ``Last-Modified``
probe for TJRO JURIS/STJ, a verified bundle's ``published_at`` for DataJud),
and they are not expected to share cadence or even the same evidence source
(that is deliberately frozen in ``docs/planning/pipeline-health-contract.md``
and must not be flattened here). What this contract does require is that all
four pipelines share the same four-state vocabulary
(``present``/``absent``/``unknown``/``unavailable``) for each clock, and that
whenever a clock is not ``present`` its own field carries a reason — not only
inferable from having read some *other* pipeline's shape, and not only from
the pipeline-wide ``aviso`` a caller might not think to check per clock.
"""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

import causaganha_mcp.tools.status as status_module
from causaganha_mcp.server import build_server


@pytest.fixture
def mcp():
    return build_server()


async def _status_fn(mcp):
    tool = await mcp.get_tool("causaganha_status")
    return tool.fn


_CLOCK_STATES = {"present", "absent", "unknown", "unavailable"}


async def test_publication_and_execution_clocks_share_vocabulary_and_reason_when_not_present(
    mcp, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    # DJEN: authority absent — nothing published yet.
    monkeypatch.setattr(
        status_module.djen_published,
        "read_published_manifest_observation",
        lambda: None,
    )
    # TJRO JURIS: authority reachable and well-formed; publication probe fails transport.
    monkeypatch.setattr(
        status_module.tjro_juris_archive,
        "read_manifest_text",
        lambda: (
            "tipo,mes_ano,ia_status,n_docs,updated_at\n"
            "ACORDAO,2026-07,uploaded,12,2026-08-23T10:00:00+00:00\n"
        ),
    )
    # STJ: authority reachable and well-formed; publication probe succeeds but exposes no
    # Last-Modified header.
    monkeypatch.setattr(
        status_module.stj_acordaos_archive,
        "read_manifest_text",
        lambda: (
            "arquivo,tipo,data_extracao,ia_status,n_registros,updated_at\n"
            "a.zip,zip,2026-08-22,uploaded,10,2026-08-23T09:00:00+00:00\n"
        ),
    )
    # DataJud: authority absent — no coherent bundle published for this tribunal.
    monkeypatch.setattr(
        status_module.datajud_state,
        "read_remote_state",
        lambda *_args, **_kwargs: None,
    )

    def _fake_head(url, **_kwargs):
        if "tjro-juris" in url:
            raise httpx.ConnectError("boom", request=httpx.Request("HEAD", url))
        return httpx.Response(200, request=httpx.Request("HEAD", url))

    monkeypatch.setattr(status_module.httpx, "head", _fake_head)

    def _fake_workflow_runs(workflow):
        if "collect-zips" in workflow:  # DJEN
            return SimpleNamespace(
                observacao="absent",
                ultima_tentativa=None,
                ultimo_sucesso=None,
                aviso="GitHub não registra runs para este workflow.",
            )
        if "tjro-sync" in workflow:
            return SimpleNamespace(
                observacao="present",
                ultima_tentativa="2026-08-23T10:00:00+00:00",
                ultimo_sucesso="2026-08-23T10:05:00+00:00",
                aviso=None,
            )
        if "stj-sync" in workflow:
            return SimpleNamespace(
                observacao="unknown",
                ultima_tentativa=None,
                ultimo_sucesso=None,
                aviso=(
                    "Nenhum run elegível apareceu na janela limitada; "
                    "runs mais antigos podem existir."
                ),
            )
        return SimpleNamespace(  # DataJud
            observacao="unavailable",
            ultima_tentativa=None,
            ultimo_sucesso=None,
            aviso="Não foi possível verificar os runs públicos do workflow: boom",
        )

    monkeypatch.setattr(status_module.workflow_runs, "observe_workflow_runs", _fake_workflow_runs)

    fn = await _status_fn(mcp)
    result = fn()

    assert {p.nome for p in result.pipelines} == {"djen", "tjro_juris", "stj_acordaos", "datajud"}

    for pipeline in result.pipelines:
        assert pipeline.publicacao_observacao in _CLOCK_STATES
        assert pipeline.execucao_observacao in _CLOCK_STATES
        if pipeline.publicacao_observacao != "present":
            assert pipeline.publicacao_aviso, (
                f"{pipeline.nome}: publicacao_observacao="
                f"{pipeline.publicacao_observacao!r} sem publicacao_aviso"
            )
        if pipeline.execucao_observacao != "present":
            assert pipeline.execucao_aviso, (
                f"{pipeline.nome}: execucao_observacao="
                f"{pipeline.execucao_observacao!r} sem execucao_aviso"
            )

    by_name = {p.nome: p for p in result.pipelines}
    assert by_name["djen"].publicacao_observacao == "absent"
    assert by_name["tjro_juris"].publicacao_observacao == "unavailable"
    assert by_name["stj_acordaos"].publicacao_observacao == "unknown"
    assert by_name["datajud"].publicacao_observacao == "absent"
