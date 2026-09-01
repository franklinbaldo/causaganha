"""Behavior contract for the product-facing ``decisoes_buscar`` tool."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from causaganha.decisoes.published import PublishedDecisionDataset
from causaganha.decisoes.search import DecisionHit, DecisionSearchResult
from causaganha_mcp.server import build_server
from causaganha_mcp.tools import decisoes


@pytest.fixture
def mcp():
    return build_server()


async def _tool_fn(mcp, name: str):
    tool = await mcp.get_tool(name)
    return tool.fn


async def test_decision_search_maps_content_and_process_next_actions(
    mcp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = PublishedDecisionDataset(fonte="stj", url="https://example/stj.parquet")
    monkeypatch.setattr(decisoes, "_datasets_for_source", lambda _fonte: ([dataset], []))
    monkeypatch.setattr(
        decisoes,
        "search_decisions",
        lambda _texto, _plan, *, limite: DecisionSearchResult(
            resultados=[
                DecisionHit(
                    fonte="stj",
                    id_documento="s1",
                    cnj="00000010220248220001",
                    data="2026-03-15",
                    tipo="REsp",
                    orgao=None,
                    relator="MIN. EXEMPLO",
                    classe="REsp",
                    trecho="Dano moral e responsabilidade civil.",
                    url=None,
                )
            ],
            datasets_consultados=1,
        ),
    )

    fn = await _tool_fn(mcp, "decisoes_buscar")
    result = fn("responsabilidade civil", fonte="stj")

    assert result.natureza == "teor"
    assert result.resultados[0].fonte == "stj"
    assert result.resultados[0].cnj == "00000010220248220001"
    assert [action["tool"] for action in result.next_actions] == [
        "processo_consultar",
        "processo_estado",
    ]


async def test_juris_thematic_search_without_period_becomes_tool_error(
    mcp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(decisoes, "_datasets_for_source", lambda _fonte: ([], []))

    fn = await _tool_fn(mcp, "decisoes_buscar")
    with pytest.raises(ToolError, match="data_inicio e data_fim"):
        fn("responsabilidade civil", fonte="juris")


async def test_coverage_limitation_survives_successful_other_source(
    mcp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = PublishedDecisionDataset(fonte="stj", url="https://example/stj.parquet")
    monkeypatch.setattr(
        decisoes,
        "_datasets_for_source",
        lambda _fonte: ([dataset], ["JURIS indisponível"]),
    )
    monkeypatch.setattr(
        decisoes,
        "search_decisions",
        lambda _texto, _plan, *, limite: DecisionSearchResult(datasets_consultados=1),
    )

    fn = await _tool_fn(mcp, "decisoes_buscar")
    result = fn(
        "responsabilidade civil",
        fonte="todas",
        data_inicio="2026-01-01",
        data_fim="2026-02-01",
    )

    assert result.resultados == []
    assert result.limitacoes == ["JURIS indisponível"]
