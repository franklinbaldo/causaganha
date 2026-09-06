"""Behavior contract for the product-facing ``decisoes_buscar`` tool."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError

from causaganha.decisoes.published import IndiceProcessualUnavailableError, PublishedDecisionDataset
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


async def test_cnj_lookup_narrows_juris_scan_to_the_indexed_file(
    mcp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A CNJ lookup must scan only the JURIS partition(s) indice_processual
    actually has for that CNJ, not every published partition (#1238) — the
    production manifest already has 1000+ of them."""
    matching = PublishedDecisionDataset(fonte="juris", url="https://example/matching.parquet")
    many_others = [
        PublishedDecisionDataset(fonte="juris", url=f"https://example/{year}-{month:02d}.parquet")
        for year in range(2018, 2027)
        for month in range(1, 13)
    ]
    monkeypatch.setattr(
        decisoes, "_datasets_for_source", lambda _fonte: ([matching, *many_others], [])
    )
    monkeypatch.setattr(
        decisoes,
        "resolve_juris_urls_for_cnj",
        lambda _cnj_digits: [matching.url],
    )
    captured: dict[str, object] = {}

    def _fake_search(
        _texto, plan, *, limite, cnj=None, offset=0, classe=None, orgao=None, relator=None
    ):
        captured["juris_urls"] = [item.url for item in plan.juris]
        return DecisionSearchResult(datasets_consultados=len(plan.juris))

    monkeypatch.setattr(decisoes, "search_decisions", _fake_search)

    fn = await _tool_fn(mcp, "decisoes_buscar")
    fn(texto=None, fonte="juris", cnj="00000010220248220001")

    assert captured["juris_urls"] == [matching.url]


def _fake_juris_manifest_datasets(count: int) -> list[PublishedDecisionDataset]:
    """A realistic-scale (1000+) fake JURIS dataset list, matching the
    production manifest's actual scale (#1241) — used to prove the index-
    unavailable failure path never opens the historical corpus."""
    return [
        PublishedDecisionDataset(fonte="juris", url=f"https://example/{i:05d}.parquet")
        for i in range(count)
    ]


async def test_cnj_lookup_fonte_juris_fails_bounded_when_index_unavailable(
    mcp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#1241: an infra failure reading indice_processual must never make a
    fonte="juris" CNJ lookup fall back to scanning every published JURIS
    partition — it must fail explicitly and boundedly instead, touching zero
    JURIS parquets."""
    datasets = _fake_juris_manifest_datasets(1200)
    assert len(datasets) > 1000
    monkeypatch.setattr(decisoes, "_datasets_for_source", lambda _fonte: (datasets, []))

    def _raise(_cnj_digits: str) -> list[str]:
        raise IndiceProcessualUnavailableError("boom")

    monkeypatch.setattr(decisoes, "resolve_juris_urls_for_cnj", _raise)

    def _fail_if_called(*_args: object, **_kwargs: object) -> DecisionSearchResult:
        pytest.fail("search_decisions must not run a JURIS scan when the index is unavailable")

    monkeypatch.setattr(decisoes, "search_decisions", _fail_if_called)

    fn = await _tool_fn(mcp, "decisoes_buscar")
    with pytest.raises(ToolError, match="[íÍ]ndice"):
        fn(texto=None, fonte="juris", cnj="00000010220248220001")


async def test_cnj_lookup_fonte_todas_omits_juris_but_keeps_other_sources_when_index_unavailable(
    mcp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#1241: fonte="todas" must not invent an unbounded JURIS scan when the
    index is unavailable — it must consult zero JURIS parquets, record an
    explicit limitation, and still return results from sources that can
    legitimately answer the same filter (stj)."""
    juris_datasets = _fake_juris_manifest_datasets(1200)
    stj_dataset = PublishedDecisionDataset(fonte="stj", url="https://example/stj.parquet")
    assert len(juris_datasets) > 1000
    monkeypatch.setattr(
        decisoes, "_datasets_for_source", lambda _fonte: ([*juris_datasets, stj_dataset], [])
    )

    def _raise(_cnj_digits: str) -> list[str]:
        raise IndiceProcessualUnavailableError("boom")

    monkeypatch.setattr(decisoes, "resolve_juris_urls_for_cnj", _raise)
    captured: dict[str, object] = {}

    def _fake_search(
        _texto, plan, *, limite, cnj=None, offset=0, classe=None, orgao=None, relator=None
    ):
        captured["juris_urls"] = [item.url for item in plan.juris]
        captured["stj_urls"] = [item.url for item in plan.stj]
        return DecisionSearchResult(datasets_consultados=len(plan.stj))

    monkeypatch.setattr(decisoes, "search_decisions", _fake_search)

    fn = await _tool_fn(mcp, "decisoes_buscar")
    result = fn(texto=None, fonte="todas", cnj="00000010220248220001")

    assert captured["juris_urls"] == []
    assert captured["stj_urls"] == [stj_dataset.url]
    assert any("juris" in msg.lower() for msg in result.limitacoes)


async def test_cnj_index_miss_is_real_absence_not_unavailability(
    mcp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#1241: a CNJ genuinely absent from indice_processual (index reachable,
    zero rows) is a real absence, not an infra failure — it must not raise
    and must not add a 'JURIS indisponível' limitation, unlike the
    index-unavailable case above."""
    dataset = PublishedDecisionDataset(fonte="juris", url="https://example/2026-02.parquet")
    monkeypatch.setattr(decisoes, "_datasets_for_source", lambda _fonte: ([dataset], []))
    monkeypatch.setattr(decisoes, "resolve_juris_urls_for_cnj", lambda _cnj_digits: [])

    fn = await _tool_fn(mcp, "decisoes_buscar")
    result = fn(texto=None, fonte="juris", cnj="00000010220248220001")

    assert result.resultados == []
    assert not any("indispon" in msg.lower() for msg in result.limitacoes)


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


def test_datasets_for_source_tcu_is_excluded_while_publication_is_unproven() -> None:
    """No verified read-back proof exists yet (#1022): the presumed
    ``TCU_PARQUET_URL`` target must never be treated as a published dataset."""
    datasets, limitations = decisoes._datasets_for_source("tcu")

    assert datasets == []
    assert any("não publicad" in item.lower() for item in limitations)


def test_datasets_for_source_todas_excludes_unproven_tcu() -> None:
    datasets, limitations = decisoes._datasets_for_source("todas")

    assert "tcu" not in [d.fonte for d in datasets]
    assert any("não publicad" in item.lower() for item in limitations)


async def test_tcu_source_fails_explicitly_while_publication_is_unproven(mcp) -> None:
    """fonte='tcu' must fail loudly instead of silently returning zero results,
    so callers can distinguish "not published" from a genuine empty search."""
    fn = await _tool_fn(mcp, "decisoes_buscar")
    with pytest.raises(ToolError, match="publicad"):
        fn("licitação", fonte="tcu")


async def test_tcu_source_is_accepted_and_results_map_to_teor(
    mcp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = PublishedDecisionDataset(fonte="tcu", url="https://example/tcu.parquet")
    monkeypatch.setattr(
        decisoes,
        "_datasets_for_source",
        lambda _fonte: ([dataset], ["TCU: cobertura restrita a 2017–2026."]),
    )
    monkeypatch.setattr(
        decisoes,
        "search_decisions",
        lambda _texto, _plan, *, limite, cnj=None, offset=0, classe=None, orgao=None, relator=None: (
            DecisionSearchResult(
                resultados=[
                    DecisionHit(
                        fonte="tcu",
                        id_documento="TCU-2026-1",
                        cnj=None,
                        data="2026-01-10",
                        tipo="Acórdão",
                        orgao="Plenário",
                        relator="Ministro Exemplo",
                        classe=None,
                        trecho="Texto autoritativo do acórdão.",
                        url=None,
                    )
                ],
                datasets_consultados=1,
            )
        ),
    )

    fn = await _tool_fn(mcp, "decisoes_buscar")
    result = fn("licitação", fonte="tcu")

    assert result.resultados[0].fonte == "tcu"
    assert result.natureza == "teor"
    assert any("2017" in item for item in result.limitacoes)
