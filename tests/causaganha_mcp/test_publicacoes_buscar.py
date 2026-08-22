"""Behavior tests for the semantic archive-first publication tool."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from causaganha.publicacoes.models import (
    CatalogoIndisponivelError,
    CoberturaArquivo,
    CriteriosInvalidosError,
    PublicacaoArquivo,
    PublicacoesBusca,
)
from causaganha_mcp.server import build_server
from causaganha_mcp.tools import publicacoes as tool_module


CNJ = "00000010220248220001"


@pytest.fixture
def mcp():
    return build_server()


async def _fn(mcp):
    tool = await mcp.get_tool("publicacoes_buscar")
    return tool.fn


def _result() -> PublicacoesBusca:
    return PublicacoesBusca(
        resultados=[
            PublicacaoArquivo(
                id="c1",
                data="2026-08-20",
                tribunal="TJRO",
                tipo="Intimação",
                orgao="1ª Vara",
                numero_processo=CNJ,
                numero_processo_mascara="0000001-02.2024.8.22.0001",
                link="https://example.test/1",
                tipo_documento="Intimação",
                classe="Procedimento Comum Cível",
                trecho=None,
                ia_item="djen-tjro-2026",
            )
        ],
        total_encontrado=1,
        pagina=1,
        limite=10,
        resultados_truncados=False,
        cobertura=CoberturaArquivo(
            status="sem_lacuna_conhecida",
            lacunas_conhecidas=0,
            arquivos_consultados=1,
            itens_consultados=1,
            aviso="Sem lacuna conhecida no catálogo.",
        ),
        criterios={"processo": CNJ, "tribunal": "TJRO"},
        consultado_em="2026-08-21T20:00:00+00:00",
    )


async def test_publicacoes_buscar_maps_archive_provenance_and_next_actions(
    mcp, monkeypatch
) -> None:
    monkeypatch.setattr(tool_module.service, "buscar_publicacoes", lambda **kwargs: _result())

    fn = await _fn(mcp)
    result = fn(processo=CNJ, tribunal="TJRO")

    assert result.total_encontrado == 1
    assert result.natureza == "arquivo"
    assert result.fonte == "CausaGanha / DJEN arquivado / Internet Archive"
    assert result.resultados[0].cnj == CNJ
    assert result.resultados[0].ia_item == "djen-tjro-2026"
    assert {action.tool for action in result.next_actions} == {
        "processo_consultar",
        "processo_estado",
    }
    assert all(action.argumentos["cnj"] == CNJ for action in result.next_actions)


async def test_zero_with_partial_coverage_is_not_described_as_proof_of_absence(
    mcp, monkeypatch
) -> None:
    partial = PublicacoesBusca(
        resultados=[],
        total_encontrado=0,
        pagina=1,
        limite=10,
        resultados_truncados=False,
        cobertura=CoberturaArquivo(
            status="parcial",
            lacunas_conhecidas=3,
            arquivos_consultados=1,
            itens_consultados=1,
            aviso="Há lacunas.",
        ),
        criterios={"tribunal": "TJRO"},
        consultado_em="2026-08-21T20:00:00+00:00",
    )
    monkeypatch.setattr(tool_module.service, "buscar_publicacoes", lambda **kwargs: partial)

    fn = await _fn(mcp)
    result = fn(tribunal="TJRO")

    assert "não permite" in result.resumo
    assert result.cobertura.status == "parcial"


async def test_validation_error_becomes_actionable_tool_error(mcp, monkeypatch) -> None:
    def fail(**kwargs):
        raise CriteriosInvalidosError("Informe ao menos um critério")

    monkeypatch.setattr(tool_module.service, "buscar_publicacoes", fail)
    fn = await _fn(mcp)

    with pytest.raises(ToolError, match="ao menos um critério"):
        fn()


async def test_catalog_failure_does_not_leak_internal_detail(mcp, monkeypatch) -> None:
    def fail(**kwargs):
        raise CatalogoIndisponivelError("/tmp/internal-secret-path")

    monkeypatch.setattr(tool_module.service, "buscar_publicacoes", fail)
    fn = await _fn(mcp)

    with pytest.raises(ToolError) as exc_info:
        fn(processo=CNJ)

    message = str(exc_info.value)
    assert "catálogo público" in message
    assert "internal-secret-path" not in message


async def test_publicacoes_buscar_has_hard_interactive_timeout(mcp) -> None:
    tool = await mcp.get_tool("publicacoes_buscar")
    assert tool.timeout == tool_module._PUBLICACOES_TOOL_TIMEOUT
