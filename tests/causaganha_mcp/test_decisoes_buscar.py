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
        lambda _texto, _plan, *, limite, cnj=None, offset=0, classe=None, orgao=None, relator=None: (
            DecisionSearchResult(
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
            )
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


async def test_cnj_lookup_bypasses_juris_thematic_period_requirement(
    mcp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = PublishedDecisionDataset(fonte="juris", url="https://example/2026-02.parquet")
    monkeypatch.setattr(decisoes, "_datasets_for_source", lambda _fonte: ([dataset], []))
    captured: dict[str, object] = {}

    def _fake_search(
        _texto, _plan, *, limite, cnj=None, offset=0, classe=None, orgao=None, relator=None
    ):
        captured["cnj"] = cnj
        return DecisionSearchResult(
            resultados=[
                DecisionHit(
                    fonte="juris",
                    id_documento="j1",
                    cnj="00000010220248220001",
                    data="2026-02-10",
                    tipo="ACÓRDÃO",
                    orgao="2ª Câmara",
                    relator="Des. Exemplo",
                    classe="Apelação",
                    trecho="Responsabilidade civil.",
                    url="https://juris.example/j1",
                )
            ],
            datasets_consultados=1,
        )

    monkeypatch.setattr(decisoes, "search_decisions", _fake_search)

    fn = await _tool_fn(mcp, "decisoes_buscar")
    result = fn(texto=None, fonte="juris", cnj="00000010220248220001")

    assert captured["cnj"] == "00000010220248220001"
    assert result.resultados[0].id_documento == "j1"


async def test_offset_is_forwarded_and_next_offset_reported_when_truncated(
    mcp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = PublishedDecisionDataset(fonte="stj", url="https://example/stj.parquet")
    monkeypatch.setattr(decisoes, "_datasets_for_source", lambda _fonte: ([dataset], []))
    captured: dict[str, object] = {}

    def _fake_search(
        _texto, _plan, *, limite, cnj=None, offset=0, classe=None, orgao=None, relator=None
    ):
        captured["offset"] = offset
        return DecisionSearchResult(
            resultados=[
                DecisionHit(
                    fonte="stj",
                    id_documento="s2",
                    cnj=None,
                    data="2026-03-14",
                    tipo="REsp",
                    orgao=None,
                    relator=None,
                    classe=None,
                    trecho=None,
                    url=None,
                )
            ],
            resultados_truncados=True,
            datasets_consultados=1,
        )

    monkeypatch.setattr(decisoes, "search_decisions", _fake_search)

    fn = await _tool_fn(mcp, "decisoes_buscar")
    result = fn("responsabilidade civil", fonte="stj", limite=1, offset=1)

    assert captured["offset"] == 1
    assert result.offset == 1
    assert result.resultados_truncados is True
    assert result.proximo_offset == 2


async def test_proximo_offset_is_none_when_not_truncated(
    mcp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = PublishedDecisionDataset(fonte="stj", url="https://example/stj.parquet")
    monkeypatch.setattr(decisoes, "_datasets_for_source", lambda _fonte: ([dataset], []))
    monkeypatch.setattr(
        decisoes,
        "search_decisions",
        lambda _texto, _plan, *, limite, cnj=None, offset=0, classe=None, orgao=None, relator=None: (
            DecisionSearchResult(resultados=[], resultados_truncados=False, datasets_consultados=1)
        ),
    )

    fn = await _tool_fn(mcp, "decisoes_buscar")
    result = fn("responsabilidade civil", fonte="stj")

    assert result.offset == 0
    assert result.proximo_offset is None


async def test_missing_texto_and_cnj_is_tool_error(mcp) -> None:
    fn = await _tool_fn(mcp, "decisoes_buscar")
    with pytest.raises(ToolError, match="texto.*cnj|cnj.*texto"):
        fn(texto=None, fonte="stj")


async def test_classe_orgao_relator_are_forwarded_to_search(
    mcp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = PublishedDecisionDataset(fonte="stj", url="https://example/stj.parquet")
    monkeypatch.setattr(decisoes, "_datasets_for_source", lambda _fonte: ([dataset], []))
    captured: dict[str, object] = {}

    def _fake_search(
        _texto,
        _plan,
        *,
        limite,
        cnj=None,
        offset=0,
        classe=None,
        orgao=None,
        relator=None,
    ):
        captured["classe"] = classe
        captured["orgao"] = orgao
        captured["relator"] = relator
        return DecisionSearchResult(datasets_consultados=1)

    monkeypatch.setattr(decisoes, "search_decisions", _fake_search)

    fn = await _tool_fn(mcp, "decisoes_buscar")
    fn(
        "responsabilidade civil",
        fonte="stj",
        classe="REsp",
        orgao="2ª Turma",
        relator="MIN. EXEMPLO",
    )

    assert captured == {"classe": "REsp", "orgao": "2ª Turma", "relator": "MIN. EXEMPLO"}


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
        lambda _texto, _plan, *, limite, cnj=None, offset=0, classe=None, orgao=None, relator=None: (
            DecisionSearchResult(datasets_consultados=1)
        ),
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
