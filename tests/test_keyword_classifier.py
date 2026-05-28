"""Tests for KeywordClassifier — deterministic zero-cost outcome detection."""

from __future__ import annotations

import pytest

from causaganha.analysis.keyword_classifier import KeywordClassifier


@pytest.fixture
def kc() -> KeywordClassifier:
    return KeywordClassifier()


# ---------------------------------------------------------------------------
# Dispositivo extraction
# ---------------------------------------------------------------------------


class TestDispositivoExtraction:
    def test_ante_o_exposto(self, kc: KeywordClassifier) -> None:
        text = "RELATÓRIO ... Ante o exposto, julgo procedente o pedido."
        disp = kc.extract_dispositivo(text)
        assert disp is not None
        assert "julgo procedente" in disp

    def test_pelo_exposto(self, kc: KeywordClassifier) -> None:
        text = "Fundamentação longa. Pelo exposto, homologo a avença."
        disp = kc.extract_dispositivo(text)
        assert disp is not None

    def test_posto_isso(self, kc: KeywordClassifier) -> None:
        text = "Em face das razões acima. Posto isso, julgo improcedente."
        disp = kc.extract_dispositivo(text)
        assert disp is not None
        assert "improcedente" in disp

    def test_no_marker_returns_none(self, kc: KeywordClassifier) -> None:
        text = "Trata-se de recurso interposto pela parte autora."
        assert kc.extract_dispositivo(text) is None

    def test_capped_at_max_chars(self, kc: KeywordClassifier) -> None:
        tail = "X" * 5000
        text = f"Ante o exposto, {tail}"
        disp = kc.extract_dispositivo(text)
        assert disp is not None
        assert len(disp) <= 2000


# ---------------------------------------------------------------------------
# High-confidence positive cases (dispositivo present)
# ---------------------------------------------------------------------------


class TestHighConfidenceCases:
    def test_julgo_procedente(self, kc: KeywordClassifier) -> None:
        text = "Ante o exposto, JULGO PROCEDENTE o pedido do autor."
        outcome, conf = kc.classify(text)
        assert outcome == "procedente"
        assert conf >= 0.85

    def test_julgo_improcedente(self, kc: KeywordClassifier) -> None:
        text = "Ante o exposto, JULGO IMPROCEDENTE o pedido formulado pelo autor."
        outcome, conf = kc.classify(text)
        assert outcome == "improcedente"
        assert conf >= 0.85

    def test_julgo_parcialmente_procedente(self, kc: KeywordClassifier) -> None:
        text = "Ante o exposto, JULGO PARCIALMENTE PROCEDENTE o pedido."
        outcome, conf = kc.classify(text)
        assert outcome == "parcialmente procedente"
        assert conf >= 0.85

    def test_homologo_acordo(self, kc: KeywordClassifier) -> None:
        text = "Ante o exposto, homologo o acordo firmado entre as partes."
        outcome, conf = kc.classify(text)
        assert outcome == "acordo"
        assert conf >= 0.85

    def test_homologo_avenca(self, kc: KeywordClassifier) -> None:
        text = "Pelo exposto, homologo a avença celebrada."
        outcome, conf = kc.classify(text)
        assert outcome == "acordo"
        assert conf >= 0.85

    def test_extingo_sem_merito(self, kc: KeywordClassifier) -> None:
        text = "Ante o exposto, extingo o processo sem resolução do mérito."
        outcome, conf = kc.classify(text)
        assert outcome == "extinto sem mérito"
        assert conf >= 0.85

    def test_pronuncio_prescricao(self, kc: KeywordClassifier) -> None:
        text = "Ante o exposto, pronuncio a prescrição e julgo extinto o processo."
        outcome, conf = kc.classify(text)
        assert outcome == "extinto sem mérito"
        assert conf >= 0.85

    def test_parcial_provimento(self, kc: KeywordClassifier) -> None:
        text = (
            "Ante o exposto, dou parcial provimento ao recurso, apenas para "
            "reduzir os danos morais de R$ 50.000 para R$ 30.000."
        )
        outcome, conf = kc.classify(text)
        assert outcome == "parcialmente procedente"
        assert conf >= 0.85

    def test_acordao_dar_provimento(self, kc: KeywordClassifier) -> None:
        text = (
            "ACÓRDÃO\n"
            "Ante o exposto, a Turma Julgadora decidiu DAR PARCIAL PROVIMENTO "
            "ao recurso de apelação."
        )
        outcome, conf = kc.classify(text)
        assert outcome == "parcialmente procedente"
        assert conf >= 0.85

    def test_procedente_em_parte(self, kc: KeywordClassifier) -> None:
        text = "Pelo exposto, julgo procedente em parte o pedido do autor."
        outcome, conf = kc.classify(text)
        assert outcome == "parcialmente procedente"
        assert conf >= 0.85

    def test_decadencia(self, kc: KeywordClassifier) -> None:
        text = "Pelo exposto, pronuncio a decadência do direito da parte autora."
        outcome, conf = kc.classify(text)
        assert outcome == "extinto sem mérito"
        assert conf >= 0.85


# ---------------------------------------------------------------------------
# Negation handling
# ---------------------------------------------------------------------------


class TestNegation:
    def test_nao_dou_provimento(self, kc: KeywordClassifier) -> None:
        text = "Ante o exposto, não dou provimento ao recurso."
        outcome, _ = kc.classify(text)
        assert outcome != "procedente", "negação não detectada: 'não dou provimento'"

    def test_nego_provimento_classified_as_improcedente(self, kc: KeywordClassifier) -> None:
        # "nego provimento" is an improcedente signal (appeal denied)
        text = "Ante o exposto, nego provimento ao recurso interposto."
        outcome, _ = kc.classify(text)
        assert outcome == "improcedente"

    def test_nao_julgo_procedente(self, kc: KeywordClassifier) -> None:
        # Contrived but tests that negation suppresses match
        text = "Ante o exposto, não julgo procedente o pedido."
        outcome, _ = kc.classify(text)
        assert outcome != "procedente"


# ---------------------------------------------------------------------------
# Procedural / unknown cases
# ---------------------------------------------------------------------------


class TestUnknownProcedural:
    def test_cite_se(self, kc: KeywordClassifier) -> None:
        text = "Defiro a petição inicial. Cite-se o réu."
        outcome, conf = kc.classify(text)
        assert outcome == "unknown"
        assert conf > 0.0

    def test_intime_se(self, kc: KeywordClassifier) -> None:
        text = "Intime-se a parte autora para manifestação no prazo de 15 dias."
        outcome, _ = kc.classify(text)
        assert outcome == "unknown"

    def test_aguarde_se(self, kc: KeywordClassifier) -> None:
        outcome, _ = kc.classify("Aguarde-se o decurso do prazo.")
        assert outcome == "unknown"

    def test_no_pattern_returns_unknown_zero(self, kc: KeywordClassifier) -> None:
        outcome, conf = kc.classify("Trata-se de recurso. As partes discutem a questão.")
        assert outcome == "unknown"
        assert conf == 0.0


# ---------------------------------------------------------------------------
# Multi-pattern boost (2+ patterns → higher confidence)
# ---------------------------------------------------------------------------


class TestMultiPatternBoost:
    def test_two_procedente_patterns_boost(self, kc: KeywordClassifier) -> None:
        text = (
            "Ante o exposto, julgo procedente o pedido do autor, "
            "condenando o réu ao pagamento de danos morais."
        )
        outcome, conf = kc.classify(text)
        assert outcome == "procedente"
        assert conf >= 0.92  # boosted by multi-match

    def test_two_acordo_patterns_boost(self, kc: KeywordClassifier) -> None:
        text = (
            "Pelo exposto, homologo o acordo firmado pelas partes, "
            "haja vista que as partes transigiram voluntariamente."
        )
        outcome, conf = kc.classify(text)
        assert outcome == "acordo"
        assert conf >= 0.92


# ---------------------------------------------------------------------------
# classify_with_dispositivo
# ---------------------------------------------------------------------------


class TestClassifyWithDispositivo:
    def test_returns_dispositivo_text(self, kc: KeywordClassifier) -> None:
        text = "Relatório ... Ante o exposto, julgo improcedente o pedido."
        outcome, conf, disp = kc.classify_with_dispositivo(text)
        assert outcome == "improcedente"
        assert conf >= 0.85
        assert disp is not None
        assert "improcedente" in disp

    def test_returns_none_dispositivo_when_no_marker(self, kc: KeywordClassifier) -> None:
        text = "Julgo procedente o pedido."  # no dispositivo marker
        outcome, conf, disp = kc.classify_with_dispositivo(text)
        assert disp is None
        assert outcome == "procedente"
        assert conf >= 0.65  # full-text match, lower confidence


# ---------------------------------------------------------------------------
# Real acórdão sample (from experiments/test_dynamic_chunking.py)
# ---------------------------------------------------------------------------


class TestRealSamples:
    ACORDAO_TEXTO = """
ACÓRDÃO

RELATÓRIO

Trata-se de apelação cível interposta por EMPRESA XYZ LTDA contra sentença
que julgou procedente o pedido de indenização por danos morais e materiais
formulado pelo autor JOSÉ DOS SANTOS.

FUNDAMENTAÇÃO

A sentença recorrida analisou de forma adequada o nexo de causalidade.

DECISÃO

Ante o exposto, por maioria de votos, a Turma Julgadora decidiu DAR PARCIAL
PROVIMENTO ao recurso de apelação, apenas para reduzir o valor da indenização
por danos morais de R$ 50.000,00 para R$ 30.000,00, mantendo inalterados os
demais termos da sentença recorrida.
"""

    SENTENCA_PROCEDENTE = """
Vistos.

Trata-se de ação ordinária proposta por JOÃO DA SILVA contra EMPRESA ABC LTDA.

Ante o exposto, JULGO PROCEDENTE o pedido do autor para condenar o réu ao
pagamento de R$ 10.000,00 a título de danos morais.

Custas e honorários a cargo do réu, fixados em 10% sobre o valor da condenação.

P.R.I.
"""

    DESPACHO = """
Manifeste-se a parte autora acerca da contestação juntada, no prazo de 15
(quinze) dias.

Após, tornem os autos conclusos para sentença.

Intime-se.
"""

    def test_acordao_parcialmente_procedente(self, kc: KeywordClassifier) -> None:
        outcome, conf = kc.classify(self.ACORDAO_TEXTO)
        assert outcome == "parcialmente procedente"
        assert conf >= 0.85

    def test_sentenca_procedente(self, kc: KeywordClassifier) -> None:
        outcome, conf = kc.classify(self.SENTENCA_PROCEDENTE)
        assert outcome == "procedente"
        assert conf >= 0.85

    def test_despacho_unknown(self, kc: KeywordClassifier) -> None:
        outcome, conf = kc.classify(self.DESPACHO)
        assert outcome == "unknown"
        assert conf > 0
