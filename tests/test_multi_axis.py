"""Testes unitários para o classificador Multi-Eixo (MultiAxisJudicialClassifier)."""

from __future__ import annotations

from causaganha.decisoes.multi_axis import MultiAxisJudicialClassifier


def test_multi_axis_acordao_apelacao_nao_provido():
    classifier = MultiAxisJudicialClassifier()
    text = (
        "TRIBUNAL DE JUSTIÇA. Apelação Cível nº 0012345-67.2024.8.22.0001. "
        "ACÓRDÃO: Vistos, relatados e discutidos estes autos, acordam os Desembargadores em "
        "negar provimento ao recurso de apelação da ré."
    )
    res = classifier.classify(text, metadata={"procedural_class": "apelação"})
    assert res.macro_categoria == "ACORDAO"
    assert res.especie_ato == "ACORDAO_APELACAO"
    assert res.desfecho_operativo == "não provido"
    assert res.polo_vencedor == "A"
    assert "segundo_grau" in res.tags


def test_multi_axis_sentenca_procedente():
    classifier = MultiAxisJudicialClassifier()
    text = (
        "PODER JUDICIÁRIO. 1ª Vara Cível. Processo nº 0001234-56.2024.8.22.0001. "
        "SENTENÇA. Ante o exposto, julgo procedente o pedido autoral para condenar a ré."
    )
    res = classifier.classify(text, metadata={"doc_type": "sentença"})
    assert res.macro_categoria == "SENTENCA"
    assert res.desfecho_operativo == "procedente"
    assert res.polo_vencedor == "A"


def test_multi_axis_cumprimento_sentenca_art_924():
    classifier = MultiAxisJudicialClassifier()
    text = (
        "Classe: Cumprimento de Sentença. "
        "SENTENÇA. Tendo em vista o pagamento voluntário e a satisfação da obrigação, "
        "julgo extinto o processo com fulcro no art. 924, inciso II, do CPC. P.R.I."
    )
    res = classifier.classify(text, metadata={"classe_hint": "Cumprimento de Sentença"})
    assert res.macro_categoria == "SENTENCA"
    assert res.especie_ato == "SENTENCA_CUMPRIMENTO_SENTENCA"
    assert res.desfecho_operativo == "extinção da execução"
    assert res.polo_vencedor == "draw"


def test_multi_axis_despacho_mero_expediente():
    classifier = MultiAxisJudicialClassifier()
    text = "DESPACHO. Dê-se vista ao Ministério Público. Intimem-se as partes."
    res = classifier.classify(text, metadata={"tipo_documento_hint": "despacho"})
    assert res.macro_categoria == "DESPACHO"
    assert res.especie_ato == "DESPACHO_MERO_EXPEDIENTE"
    assert res.desfecho_operativo == "despacho de expediente"


def test_multi_axis_tutela_urgencia_interlocutoria():
    classifier = MultiAxisJudicialClassifier()
    text = (
        "DECISÃO INTERLOCUTÓRIA. Trata-se de pedido liminar. "
        "Presentes os requisitos do art. 300 do CPC, defiro o pedido de tutela de urgência."
    )
    res = classifier.classify(text, metadata={"doc_type": "decisão"})
    assert res.macro_categoria == "DECISAO_INTERLOCUTORIA"
    assert res.especie_ato == "DECISAO_TUTELA_URGENCIA_LIMINAR"
    assert res.desfecho_operativo == "tutela deferida"
    assert res.polo_vencedor == "A"


def test_multi_axis_recurso_inominado_parcialmente_provido():
    classifier = MultiAxisJudicialClassifier()
    text = (
        "TURMA RECURSAL DOS JUIZADOS ESPECIAIS. Recurso Inominado Cível. "
        "ACÓRDÃO. Acordam os membros da Turma Recursal em dar parcial provimento ao recurso."
    )
    res = classifier.classify(text, metadata={"classe_processual": "recurso inominado"})
    assert res.macro_categoria == "ACORDAO"
    assert res.especie_ato == "ACORDAO_RECURSO_INOMINADO"
    assert res.desfecho_operativo == "parcialmente provido"
    assert res.polo_vencedor == "draw"


def test_multi_axis_to_dict():
    classifier = MultiAxisJudicialClassifier()
    text = "SENTENÇA. Julgo improcedente o pedido."
    res = classifier.classify(text, metadata={"doc_type": "sentença"})
    d = res.to_dict()
    assert d["macro_categoria"] == "SENTENCA"
    assert d["desfecho_operativo"] == "improcedente"
    assert d["polo_vencedor"] == "P"
    assert "confianca_desfecho" in d
