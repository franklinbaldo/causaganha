"""Testes unitários para o classificador Multi-Eixo, Classe Processual (DataJud/TPU) e ML Fallback."""

from __future__ import annotations

from pathlib import Path
import sqlite3

from causaganha.decisoes.classe_processual import (
    ClasseProcessualExtractor,
    DataJudAcervoReader,
)
from causaganha.decisoes.ml_fallback import WeakSupervisionOutcomeFallback
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
    assert res.classe_codigo == 198
    assert res.classe_nome == "Apelação Cível"
    assert res.desfecho_operativo == "não provido"
    assert res.polo_vencedor == "A"
    assert "segundo_grau" in res.tags


def test_multi_axis_sentenca_procedente():
    classifier = MultiAxisJudicialClassifier()
    text = (
        "PODER JUDICIÁRIO. 1ª Vara Cível. Processo nº 0001234-56.2024.8.22.0001. "
        "Classe: PROCEDIMENTO COMUM CÍVEL (7). "
        "SENTENÇA. Ante o exposto, julgo procedente o pedido autoral para condenar a ré."
    )
    res = classifier.classify(text, metadata={"doc_type": "sentença"})
    assert res.macro_categoria == "SENTENCA"
    assert res.classe_codigo == 7
    assert res.origem_classe == "cabecalho_ner"
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
    assert res.classe_codigo == 156
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
        "ACÓRDÃO. Acordam os membros da Turma Recursal em conhecer do recurso para dar-lhe parcial provimento."
    )
    res = classifier.classify(text, metadata={"classe_processual": "recurso inominado"})
    assert res.macro_categoria == "ACORDAO"
    assert res.especie_ato == "ACORDAO_RECURSO_INOMINADO"
    assert res.classe_codigo == 460
    assert res.desfecho_operativo == "parcialmente provido"
    assert res.polo_vencedor == "draw"


def test_multi_axis_appellate_polarity_institutional_defendant():
    classifier = MultiAxisJudicialClassifier()
    text = (
        "APELAÇÃO CÍVEL (198) nº 0800123-45.2025.8.10.0001\n"
        "APELANTE: BANCO BRADESCO S.A.\n"
        "APELADO: JOAO DA SILVA\n"
        "ACÓRDÃO: Acordam os Desembargadores em conhecer do recurso e negar-lhe provimento."
    )
    res = classifier.classify(text)
    assert res.classe_codigo == 198
    assert res.desfecho_operativo == "não provido"
    # Banco apelou ('P') e teve recurso não provido -> Autor ('A') venceu
    assert res.polo_vencedor == "A"


def test_datajud_acervo_reader_sqlite_integration(tmp_path: Path):
    db_file = tmp_path / "acervo.sqlite"
    con = sqlite3.connect(db_file)
    con.executescript(
        """
        CREATE TABLE registros (id INTEGER PRIMARY KEY, numero_processo TEXT, grau TEXT);
        CREATE TABLE orgaos (id INTEGER PRIMARY KEY, nome TEXT);
        CREATE TABLE capas (id INTEGER PRIMARY KEY, classe_codigo INTEGER, classe_nome TEXT, orgao_id INTEGER);
        CREATE TABLE observacoes (id INTEGER PRIMARY KEY, registro_id INTEGER, capa_id INTEGER);
        CREATE TABLE assuntos (id INTEGER PRIMARY KEY, registro_id INTEGER, nome TEXT);
        CREATE TABLE tipos_movimento (id INTEGER PRIMARY KEY, codigo INTEGER, nome TEXT);
        CREATE TABLE movimentos (id INTEGER PRIMARY KEY, registro_id INTEGER, tipo_id INTEGER, instante INTEGER);

        INSERT INTO registros VALUES (1, '70012345620258220001', 'G1');
        INSERT INTO orgaos VALUES (10, '1ª Vara Cível de Porto Velho');
        INSERT INTO capas VALUES (100, 436, 'Procedimento do Juizado Especial Cível', 10);
        INSERT INTO observacoes VALUES (1000, 1, 100);
        INSERT INTO assuntos VALUES (50, 1, 'Indenização por Dano Moral');
        INSERT INTO tipos_movimento VALUES (20, 219, 'Procedência');
        INSERT INTO movimentos VALUES (300, 1, 20, 1700000000);
        """
    )
    con.commit()
    con.close()

    reader = DataJudAcervoReader(db_path=db_file)
    extractor = ClasseProcessualExtractor(acervo_reader=reader)
    classifier = MultiAxisJudicialClassifier(classe_extractor=extractor)

    res = classifier.classify(
        "Processo nº 7001234-56.2025.8.22.0001. Sentença proferida nos autos.",
        metadata={"doc_type": "sentença"},
    )
    assert res.classe_codigo == 436
    assert res.classe_nome == "Procedimento do Juizado Especial Cível"
    assert res.origem_classe == "datajud_acervo"
    assert res.assunto_principal == "Indenização por Dano Moral"
    assert res.datajud_desfecho_tpu == "procedente"
    assert res.desfecho_operativo == "procedente"
    assert res.polo_vencedor == "A"


def test_weak_supervision_ml_fallback():
    fb = WeakSupervisionOutcomeFallback(min_proba=0.25)
    n = fb.fit_from_corpus(
        texts=[
            "Decisão interlocutória deferindo a tutela de urgência liminar para fornecimento de cirurgia.",
            "Sentença julgando procedente o pedido inicial e condenando o requerido.",
        ],
        labels=["tutela deferida", "procedente"],
        confidences=[0.95, 0.95],
    )
    assert n > 20
    pred = fb.predict("Presentes os requisitos legais, defiro a tutela de urgência liminar.")
    assert pred.category == "tutela deferida"
    assert pred.confidence >= 0.55


def test_multi_axis_to_dict():
    classifier = MultiAxisJudicialClassifier()
    text = "SENTENÇA. Julgo improcedente o pedido."
    res = classifier.classify(text, metadata={"doc_type": "sentença"})
    d = res.to_dict()
    assert d["macro_categoria"] == "SENTENCA"
    assert d["desfecho_operativo"] == "improcedente"
    assert d["polo_vencedor"] == "P"
    assert "classe_codigo" in d
    assert "classe_nome" in d
    assert "origem_classe" in d
    assert "confianca_desfecho" in d
