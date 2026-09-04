"""Period-only listing contract for ``decisoes_buscar``."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from causaganha.decisoes.published import PublishedDecisionDataset
from causaganha.decisoes.search import DecisionHit, DecisionSearchResult
from causaganha_mcp.server import build_server
from causaganha_mcp.tools import decisoes


async def _fn():
    mcp = build_server()
    tool = await mcp.get_tool("decisoes_buscar")
    return tool.fn


async def test_period_without_text_lists_decisions(monkeypatch: pytest.MonkeyPatch) -> None:
    dataset = PublishedDecisionDataset(
        fonte="juris",
        url="https://example/2026-09.parquet",
        periodo="2026-09",
    )
    monkeypatch.setattr(decisoes, "_datasets_for_source", lambda _fonte: ([dataset], []))
    captured: dict[str, object] = {}

    def fake_search(
        texto,
        _plan,
        *,
        limite,
        cnj=None,
        offset=0,
        classe=None,
        orgao=None,
        relator=None,
    ):
        captured["texto"] = texto
        captured["limite"] = limite
        return DecisionSearchResult(
            resultados=[
                DecisionHit(
                    fonte="juris",
                    id_documento="j-hoje",
                    cnj="00000010220248220001",
                    data="2026-09-04",
                    tipo="SENTENÇA",
                    orgao="1ª Vara",
                    relator=None,
                    classe="Procedimento Comum",
                    trecho="Sentença publicada no período.",
                    url="https://juris.example/j-hoje",
                )
            ],
            datasets_consultados=1,
        )

    monkeypatch.setattr(decisoes, "search_decisions", fake_search)
    fn = await _fn()
    result = fn(
        texto=None,
        fonte="juris",
        data_inicio="2026-09-04",
        data_fim="2026-09-04",
        limite=50,
    )

    assert captured == {"texto": "%%", "limite": 50}
    assert result.resultados[0].id_documento == "j-hoje"
    assert result.data_inicio == "2026-09-04"
    assert result.data_fim == "2026-09-04"
    assert [item["tool"] for item in result.next_actions] == [
        "processo_consultar",
        "processo_estado",
    ]


async def test_period_without_text_requires_both_dates() -> None:
    fn = await _fn()
    with pytest.raises(ToolError, match="data_inicio e data_fim"):
        fn(texto=None, fonte="juris", data_inicio="2026-09-04")


async def test_period_without_text_is_limited_to_31_days() -> None:
    fn = await _fn()
    with pytest.raises(ToolError, match="31 dias"):
        fn(
            texto=None,
            fonte="stj",
            data_inicio="2026-01-01",
            data_fim="2026-02-01",
        )
