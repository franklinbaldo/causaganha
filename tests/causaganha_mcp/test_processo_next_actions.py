"""Composition hints returned by ``processo_consultar`` stay explicit and testable."""

from __future__ import annotations

from causaganha.processos.models import JurisDecisao, ProcessoConsultaResult, StjAcordao
from causaganha_mcp.tools.processo import _next_actions


CNJ = "00000010220248220001"
CNJ_MASCARA = "0000001-02.2024.8.22.0001"


def _result(*, encontrado: bool, **kwargs: object) -> ProcessoConsultaResult:
    return ProcessoConsultaResult(
        encontrado=encontrado,
        nr_processo=CNJ,
        nr_processo_mascara=CNJ_MASCARA,
        **kwargs,
    )


def test_next_actions_offer_archive_and_live_composition() -> None:
    actions = _next_actions(_result(encontrado=True))

    assert [action.tool for action in actions] == ["processo_estado", "publicacoes_buscar"]
    assert actions[0].argumentos == {"cnj": CNJ}
    assert actions[1].argumentos == {"processo": CNJ}
    assert "live" in actions[0].acao.lower()
    assert "arquivadas" in actions[1].acao.lower()


def test_not_found_snapshot_still_offers_independent_next_checks() -> None:
    actions = _next_actions(_result(encontrado=False))

    assert {action.tool for action in actions} == {"processo_estado", "publicacoes_buscar"}
    assert all(action.argumentos for action in actions)


def test_stj_document_offers_explicit_teor_route_by_cnj() -> None:
    stj = StjAcordao(
        id="s1",
        classe="REsp",
        relator="MIN. EXEMPLO",
        tema="Responsabilidade civil",
        tese=None,
        ementa="Recurso especial. Dano moral.",
        data_decisao="2026-03-15",
        data_publicacao=None,
    )
    actions = _next_actions(_result(encontrado=True, stj=stj))

    teor_actions = [action for action in actions if action.tool == "decisoes_buscar"]
    assert len(teor_actions) == 1
    assert teor_actions[0].argumentos == {"cnj": CNJ, "fonte": "stj"}
    assert "teor" in teor_actions[0].acao.lower()


def test_juris_document_offers_explicit_teor_route_by_cnj() -> None:
    juris = JurisDecisao(
        n_documentos=1,
        tipos=["ACÓRDÃO"],
        data_julgamento="2026-02-10",
        orgao="2ª Câmara",
        relator="Des. Exemplo",
        classe="Apelação",
        url="https://juris.example/j1",
    )
    actions = _next_actions(_result(encontrado=True, juris=juris))

    teor_actions = [action for action in actions if action.tool == "decisoes_buscar"]
    assert len(teor_actions) == 1
    assert teor_actions[0].argumentos == {"cnj": CNJ, "fonte": "juris"}


def test_no_juris_or_stj_document_offers_no_teor_route() -> None:
    actions = _next_actions(_result(encontrado=True))

    assert all(action.tool != "decisoes_buscar" for action in actions)
