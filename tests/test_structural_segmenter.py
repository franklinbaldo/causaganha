"""Testes unitários para o FullDocumentStructuralSegmenter."""

from __future__ import annotations

import pytest
from causaganha.decisoes.structural_segmenter import (
    FullDocumentStructuralSegmenter,
    SectionType,
    DocumentStructure,
)
from causaganha.decisoes.topology_router import DecisionTopology


def test_segment_complete_sentenca():
    doc_text = (
        "PODER JUDICIÁRIO DO ESTADO DE RONDÔNIA\n"
        "Comarca de Porto Velho - 3ª Vara Cível\n"
        "Processo nº 7001234-56.2024.8.22.0001\n"
        "Autor: João da Silva\n"
        "Réu: Banco Exemplo S/A\n\n"
        "RELATÓRIO\n"
        "Trata-se de ação de obrigação de fazer c/c indenização por danos morais.\n"
        "O autor alega cobrança indevida em sua conta corrente e pede R$ 10.000,00 de danos morais.\n"
        "A instituição financeira ré apresentou contestação alegando exercício regular de direito.\n\n"
        "FUNDAMENTAÇÃO\n"
        "Passo ao julgamento do mérito nos termos do art. 355, I, do CPC.\n"
        "A relação entre as partes é de consumo, regida pelo CDC.\n"
        "Restou incontroversa a falha na prestação de serviços bancários gerando dano moral presumido.\n\n"
        "DISPOSITIVO\n"
        "Ante o exposto, julgo procedente o pedido formulado na inicial para condenar a ré ao pagamento de R$ 8.000,00 a título de indenização.\n\n"
        "HONORÁRIOS E CUSTAS\n"
        "Condeno o requerido ao pagamento das custas processuais e honorários advocatícios sucumbenciais de 15% sobre a condenação.\n\n"
        "ENCERRAMENTO\n"
        "Publique-se. Registre-se. Intimem-se.\n"
        "Porto Velho, 20 de outubro de 2024.\n"
        "Dr. Fulano de Tal - Juiz de Direito\n"
    )

    segmenter = FullDocumentStructuralSegmenter()
    meta = {
        "classe_processual": "Procedimento Comum Cível",
        "orgao_julgador": "3ª Vara Cível",
    }
    struct = segmenter.segment(doc_text, metadata=meta)

    assert isinstance(struct, DocumentStructure)
    assert struct.topology == DecisionTopology.SENTENCA
    secs = struct.sections

    # Garante presença das seções essenciais
    assert "cabecalho" in secs
    assert "relatorio" in secs
    assert "fundamentacao" in secs
    assert "dispositivo" in secs
    assert "encerramento" in secs

    # Validação do conteúdo
    assert "7001234-56.2024.8.22.0001" in secs["cabecalho"].text
    assert "Trata-se de ação" in secs["relatorio"].text
    assert "Passo ao julgamento" in secs["fundamentacao"].text
    assert "julgo procedente" in secs["dispositivo"].text
    assert "Publique-se" in secs["encerramento"].text

    # Validação de entidades extraídas
    assert struct.entities.get("numero_cnj") == "7001234-56.2024.8.22.0001"
    assert any("8.000,00" in v for v in struct.entities.get("valores_monetarios", []))


def test_segment_complete_acordao():
    doc_text = (
        "TRIBUNAL DE JUSTIÇA DE RONDÔNIA\n"
        "2ª Câmara Cível - Apelação Cível nº 7000109-66.2024.8.22.0000\n"
        "Relator: Desembargador Gilberto Barbosa\n"
        "Apelante: Consumidor Lesado\n"
        "Apelado: Companhia Elétrica\n\n"
        "EMENTA\n"
        "DIREITO DO CONSUMIDOR. APELAÇÃO CÍVEL. CORTE INDEVIDO DE ENERGIA. DANO MORAL CONFIGURADO. RECURSO PROVIDO.\n\n"
        "RELATÓRIO\n"
        "Trata-se de apelação cível interposta contra sentença de improcedência.\n\n"
        "VOTO\n"
        "O Senhor Desembargador Gilberto Barbosa (Relator): Passo ao voto condutor. A jurisprudência consolidada no STJ é uníssona.\n\n"
        "ACÓRDÃO DECISÓRIO\n"
        "Vistos, relatados e discutidos estes autos, acordam os Desembargadores da 2ª Câmara Cível em dar provimento ao recurso, à unanimidade.\n\n"
        "ENCERRAMENTO\n"
        "Porto Velho, 15 de maio de 2025. Desembargador Gilberto Barbosa - Relator\n"
    )

    segmenter = FullDocumentStructuralSegmenter()
    meta = {
        "classe_processual": "Apelação Cível",
        "relator": "Desembargador Gilberto Barbosa",
        "doc_type": "acordao",
    }
    struct = segmenter.segment(doc_text, metadata=meta)

    assert struct.topology == DecisionTopology.ACORDAO
    secs = struct.sections
    assert "cabecalho" in secs
    assert "ementa" in secs
    assert "voto" in secs or "fundamentacao" in secs
    assert "dispositivo" in secs
    assert "acordam os Desembargadores" in secs["dispositivo"].text


def test_monotonic_structural_order():
    # Garante que as seções preservam rigorosamente a ordem de leitura
    doc_text = (
        "PODER JUDICIÁRIO. Vara Cível.\n"
        "RELATÓRIO. Trata-se de ação.\n"
        "FUNDAMENTAÇÃO. Passo a decidir o mérito.\n"
        "DISPOSITIVO. Ante o exposto, julgo improcedente.\n"
        "Publique-se. Juiz de Direito."
    )
    segmenter = FullDocumentStructuralSegmenter()
    struct = segmenter.segment(doc_text)

    # Verifica se os offsets são estritamente crescentes
    last_end = 0
    for sec_name, span in struct.sections.items():
        assert span.start >= last_end, f"Seção {sec_name} começa antes do fim da anterior"
        assert span.end > span.start
        last_end = span.end
