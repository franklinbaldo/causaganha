"""Composition hints returned by ``processo_consultar`` stay explicit and testable."""

from __future__ import annotations

from causaganha.processos.models import ProcessoConsultaResult
from causaganha_mcp.tools.processo import _next_actions


CNJ = "00000010220248220001"
CNJ_MASCARA = "0000001-02.2024.8.22.0001"


def _result(*, encontrado: bool) -> ProcessoConsultaResult:
    return ProcessoConsultaResult(
        encontrado=encontrado,
        nr_processo=CNJ,
        nr_processo_mascara=CNJ_MASCARA,
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
