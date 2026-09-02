"""Integrated ARQUIVO -> ESTADO -> TEOR contract (issue #891).

`processo_consultar` (ARQUIVO), `processo_estado` (ESTADO) and
`decisoes_buscar` (TEOR) are each unit-tested in isolation already. What is
still missing is a single proof that the three compose correctly for the
*same* CNJ: every response keeps its own nature/provenance/época distinct,
`next_actions` reuse arguments the agent already has instead of decorative
text, no tool silently calls another behind the agent's back, and absence in
one source is never presented as absence of teor.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
import respx

from causaganha.decisoes.published import PublishedDecisionDataset
from causaganha.decisoes.search import DecisionHit, DecisionSearchResult
from causaganha.processos.models import FonteCobertura, ProcessoConsultaResult, StjAcordao
from causaganha_mcp.server import build_server
from causaganha_mcp.tools import datajud_processo as datajud_processo_module
from causaganha_mcp.tools import decisoes as decisoes_module
from causaganha_mcp.tools import processo as processo_module
from datajud.client import search_endpoint


CNJ = "00000010220248220001"
CNJ_MASCARA = "0000001-02.2024.8.22.0001"
TRIBUNAL = "tjro"
ENDPOINT = search_endpoint(TRIBUNAL)

# Old enough to cross service.buscar_processo's 48h staleness threshold — the
# tool layer is stubbed directly here, so the aviso text below stands in for
# what `_aviso_snapshot_desatualizado` would have produced.
_STALE_DATASET_GERADO_EM = "2020-01-01T00:00:00Z"
_STALE_AVISO = (
    "Snapshot gerado há muitas horas (> 48h) — consulte processo_estado "
    "(DataJud live) se a pergunta depender de andamento recente."
)


def _arquivo_result(*, encontrado: bool = True) -> ProcessoConsultaResult:
    if not encontrado:
        return ProcessoConsultaResult(
            encontrado=False, nr_processo=CNJ, nr_processo_mascara=CNJ_MASCARA
        )
    return ProcessoConsultaResult(
        encontrado=True,
        nr_processo=CNJ,
        nr_processo_mascara=CNJ_MASCARA,
        fontes_presentes=["djen", "stj"],
        cobertura_dataset=[FonteCobertura(fonte="djen", status="loaded_remote", registros=10)],
        stj=StjAcordao(
            id="stj-1",
            classe="REsp",
            relator="MIN X",
            tema="tema",
            tese="tese",
            ementa="ementa",
            data_decisao="2024-05-01",
            data_publicacao="2024-05-10",
        ),
        dataset_gerado_em=_STALE_DATASET_GERADO_EM,
        avisos=[_STALE_AVISO],
    )


def _datajud_source(*, movimentos: list[dict]) -> dict:
    return {
        "numeroProcesso": CNJ,
        "tribunal": TRIBUNAL.upper(),
        "grau": "G2",
        "classe": {"codigo": 7, "nome": "Apelação Cível"},
        "assuntos": [{"codigo": 1, "nome": "Contratos"}],
        "orgaoJulgador": {"codigo": 20, "nome": "2ª Câmara"},
        "dataAjuizamento": "20240102030405",
        "dataHoraUltimaAtualizacao": "2026-08-21T13:00:00Z",
        "movimentos": movimentos,
    }


def _datajud_payload_with_decision_movement() -> dict:
    return {
        "hits": {
            "hits": [
                {
                    "_source": _datajud_source(
                        movimentos=[
                            {
                                "codigo": 246,
                                "nome": "Julgamento",
                                "dataHora": "2026-08-21T13:00:00Z",
                            }
                        ]
                    )
                }
            ]
        }
    }


def _teor_result() -> DecisionSearchResult:
    return DecisionSearchResult(
        resultados=[
            DecisionHit(
                fonte="stj",
                id_documento="stj-1",
                cnj=CNJ,
                data="2024-05-01",
                tipo="REsp",
                orgao=None,
                relator="MIN X",
                classe="REsp",
                trecho="Recurso especial. Dano moral.",
                url=None,
            )
        ],
        datasets_consultados=1,
    )


@pytest.fixture
def mcp():
    return build_server()


async def _tool_fn(mcp, name: str):
    tool = await mcp.get_tool(name)
    return tool.fn


async def test_arquivo_estado_teor_compose_without_hidden_cross_calls(
    mcp, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same CNJ across the three tools: distinct provenance, honest next_actions, no leaks."""
    # -- ARQUIVO --------------------------------------------------------
    monkeypatch.setattr(
        processo_module.service, "buscar_processo", lambda *a, **k: _arquivo_result()
    )
    real_consultar_processo = datajud_processo_module.process_service.consultar_processo
    estado_spy = AsyncMock(
        side_effect=AssertionError("processo_consultar chamou o DataJud (ESTADO) escondido")
    )
    monkeypatch.setattr(datajud_processo_module.process_service, "consultar_processo", estado_spy)
    teor_spy = MagicMock(
        side_effect=AssertionError("processo_consultar chamou a busca de TEOR escondida")
    )
    monkeypatch.setattr(decisoes_module, "search_decisions", teor_spy)

    arquivo_fn = await _tool_fn(mcp, "processo_consultar")
    arquivo = arquivo_fn(cnj=CNJ)

    estado_spy.assert_not_called()
    teor_spy.assert_not_called()

    assert arquivo.fonte == "parquet_ia"
    assert arquivo.canonica is True
    assert arquivo.dataset_gerado_em == _STALE_DATASET_GERADO_EM
    assert arquivo.consultado_em != arquivo.dataset_gerado_em
    assert any("processo_estado" in aviso for aviso in arquivo.avisos)

    estado_action = next(a for a in arquivo.next_actions if a.tool == "processo_estado")
    assert estado_action.argumentos == {"cnj": CNJ}
    teor_action = next(a for a in arquivo.next_actions if a.tool == "decisoes_buscar")
    assert teor_action.argumentos == {"cnj": CNJ, "fonte": "stj"}

    # -- ESTADO -----------------------------------------------------------
    # The ARQUIVO phase above only needed to prove ESTADO/TEOR were never
    # reached; restore the real DataJud call now that ESTADO itself is under
    # test (respx mocks the transport below, not this service function).
    monkeypatch.setattr(
        datajud_processo_module.process_service, "consultar_processo", real_consultar_processo
    )
    arquivo_spy = MagicMock(
        side_effect=AssertionError("processo_estado chamou o ARQUIVO escondido")
    )
    monkeypatch.setattr(processo_module.service, "buscar_processo", arquivo_spy)

    estado_fn = await _tool_fn(mcp, "processo_estado")
    with respx.mock() as router:
        router.post(ENDPOINT).respond(200, json=_datajud_payload_with_decision_movement())
        estado = await estado_fn(cnj=CNJ, tribunal=TRIBUNAL)

    arquivo_spy.assert_not_called()
    teor_spy.assert_not_called()

    assert estado.natureza == "estado"
    assert estado.fonte_oficial == "DataJud/CNJ"
    assert estado.encontrado is True
    assert all(m.nome for m in estado.marcos)  # a movement name, never a teor excerpt

    arquivo_route = next(a for a in estado.next_actions if a.tool == "processo_consultar")
    assert arquivo_route.argumentos == {"cnj": estado.cnj_formatado}
    teor_route = next(a for a in estado.next_actions if a.tool == "decisoes_buscar")
    assert teor_route.argumentos == {"cnj": estado.cnj_formatado}
    # ESTADO proves the event happened; it must not claim to know its content.
    assert "não" in teor_route.quando.lower()

    # -- TEOR ---------------------------------------------------------------
    dataset = PublishedDecisionDataset(fonte="stj", url="https://example/stj.parquet")
    monkeypatch.setattr(decisoes_module, "_datasets_for_source", lambda _fonte: ([dataset], []))
    monkeypatch.setattr(decisoes_module, "search_decisions", lambda *a, **k: _teor_result())

    teor_fn = await _tool_fn(mcp, "decisoes_buscar")
    teor = teor_fn(cnj=CNJ, fonte="stj")

    arquivo_spy.assert_not_called()
    estado_spy.assert_not_called()

    assert teor.natureza == "teor"
    assert teor.resultados[0].cnj == CNJ
    assert teor.resultados[0].fonte == "stj"
    assert {a["tool"] for a in teor.next_actions} == {"processo_consultar", "processo_estado"}


async def test_absence_in_one_source_is_never_presented_as_absence_of_teor(
    mcp, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A CNJ absent from the archive/DataJud must never be reported as 'sem teor'."""
    monkeypatch.setattr(
        processo_module.service,
        "buscar_processo",
        lambda *a, **k: _arquivo_result(encontrado=False),
    )
    arquivo_fn = await _tool_fn(mcp, "processo_consultar")
    arquivo = arquivo_fn(cnj=CNJ)
    assert arquivo.encontrado is False
    assert not any(
        "sem decis" in aviso.lower() or "não existe" in aviso.lower() for aviso in arquivo.avisos
    )

    estado_fn = await _tool_fn(mcp, "processo_estado")
    with respx.mock() as router:
        router.post(ENDPOINT).respond(200, json={"hits": {"hits": []}})
        estado = await estado_fn(cnj=CNJ, tribunal=TRIBUNAL)
    assert estado.encontrado is False
    assert any("não significa" in item for item in estado.limitacoes)

    monkeypatch.setattr(decisoes_module, "_datasets_for_source", lambda _fonte: ([], []))
    monkeypatch.setattr(
        decisoes_module,
        "search_decisions",
        lambda *a, **k: DecisionSearchResult(resultados=[], datasets_consultados=0),
    )
    teor_fn = await _tool_fn(mcp, "decisoes_buscar")
    teor = teor_fn(cnj=CNJ, fonte="todas")
    assert teor.resultados == []
    assert "0 resultado" in teor.resumo
