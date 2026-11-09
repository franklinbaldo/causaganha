"""Testes unitários para o TopologyRouter baseado em metadados do DJEN."""

from __future__ import annotations

from causaganha.decisoes.topology_router import DecisionTopology, TopologyRouter


def test_route_explicit_doc_type():
    assert TopologyRouter.route({"doc_type": "acordao"}) == DecisionTopology.ACORDAO
    assert TopologyRouter.route({"tipo_comunicacao": "sentenca"}) == DecisionTopology.SENTENCA
    assert TopologyRouter.route({"doc_type": "despacho"}) == DecisionTopology.INTERLOCUTORIA


def test_route_by_relator_and_court():
    meta = {
        "relator": "Desembargador Gilberto Barbosa",
        "orgao_julgador": "2ª Câmara Cível",
        "tribunal": "TJRO",
    }
    assert TopologyRouter.route(meta) == DecisionTopology.ACORDAO


def test_route_by_execucao_class():
    meta = {
        "classe_processual": "Cumprimento de Sentença contra a Fazenda Pública",
        "orgao_julgador": "1ª Vara de Fazenda Pública",
    }
    assert TopologyRouter.route(meta) == DecisionTopology.EXECUCAO

    meta_exec = {
        "classe": "Execução Fiscal",
        "vara": "Vara de Execuções Fiscais",
    }
    assert TopologyRouter.route(meta_exec) == DecisionTopology.EXECUCAO


def test_route_by_sentenca_class():
    meta = {
        "classe_processual": "Procedimento do Juizado Especial Cível",
        "vara": "1º Juizado Especial Cível de Porto Velho",
    }
    assert TopologyRouter.route(meta) == DecisionTopology.SENTENCA


def test_route_fallback_header():
    # Sem metadados, deduz pelo texto institucional do cabeçalho
    text_acordao = (
        "PODER JUDICIÁRIO. Tribunal de Justiça de Rondônia. ACÓRDÃO. Sessão eletrônica n. 953."
    )
    assert TopologyRouter.route({}, text=text_acordao) == DecisionTopology.ACORDAO

    text_sentenca = "PODER JUDICIÁRIO. Comarca de Ariquemes. 2ª Vara Cível. SENTENÇA. Vistos etc."
    assert TopologyRouter.route({}, text=text_sentenca) == DecisionTopology.SENTENCA
