"""Classificador Fallback via Supervisão Fraca / Distante (TF-IDF + Random Forest).

Atua como rede de segurança calibrada quando o `RegexTournament` retorna `unknown`:
1. Treina sobre exemplos de alta confiança do próprio `RegexTournament` (Weak Supervision)
   e/ou sobre movimentos oficiais da TPU do CNJ no `acervo.sqlite` do DataJud (Distant Supervision),
   combinados com um conjunto canônico de dispositivos sementes.
2. Extrai n-gramas (1, 2) via TF-IDF do trecho final / dispositivo da decisão.
3. Aplica restrição ortogonal de domínio por `macro_categoria` (Eixo 1 -> Eixo 2):
   ex.: uma `SENTENCA` só pode receber desfechos de 1º grau/execução; um `ACORDAO` só pode
   receber desfechos recursais/colegiados.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer

# Restrição de domínio entre Eixo 1 (Macro-Categoria) e Eixo 2 (Desfechos Permitidos no ML Fallback)
ALLOWED_OUTCOMES_BY_MACRO: dict[str, frozenset[str]] = {
    "SENTENCA": frozenset(
        {
            "procedente",
            "improcedente",
            "parcialmente procedente",
            "extinto sem mérito",
            "acordo",
            "extinção da execução",
            "homologação de decisão leiga",
        }
    ),
    "ACORDAO": frozenset(
        {
            "provido",
            "não provido",
            "parcialmente provido",
            "não conhecido",
            "acordo",
        }
    ),
    "DECISAO_MONOCRATICA": frozenset(
        {
            "provido",
            "não provido",
            "parcialmente provido",
            "não conhecido",
            "tutela deferida",
            "tutela indeferida",
        }
    ),
    "DECISAO_INTERLOCUTORIA": frozenset(
        {
            "tutela deferida",
            "tutela indeferida",
            "extinção da execução",
            "despacho de expediente",
            "acordo",
        }
    ),
}

# Exemplos canônicos por categoria para garantir inicialização imediata (cold-start)
_CANONICAL_SEED_CORPUS: list[tuple[str, str]] = [
    (
        "Ante o exposto, julgo procedente o pedido autoral para condenar a parte ré ao pagamento de indenização por danos morais e materiais.",
        "procedente",
    ),
    (
        "Posto isso, acolho integralmente a pretensão inicial, confirmando a tutela concedida e condenando o requerido nas custas e honorários.",
        "procedente",
    ),
    (
        "Concedo a segurança pleiteada no mandado de segurança para determinar o fornecimento do medicamento e autorizo o levantamento do alvará.",
        "procedente",
    ),
    (
        "Ante o exposto, julgo improcedente o pedido formulado na inicial, extinguindo o feito com resolução de mérito nos termos do art. 487, I, do CPC.",
        "improcedente",
    ),
    (
        "Rejeito integralmente a pretensão autoral por ausência de ato ilícito e absolvo o acusado das imputações constantes na denúncia.",
        "improcedente",
    ),
    (
        "Denego a segurança impetrada e condeno a parte autora ao pagamento das custas processuais, observada a gratuidade da justiça.",
        "improcedente",
    ),
    (
        "Ante o exposto, julgo parcialmente procedentes os pedidos iniciais para condenar o banco réu à restituição em dobro e afastar o dano moral.",
        "parcialmente procedente",
    ),
    (
        "Acolho em parte a pretensão autoral, reconhecendo a sucumbência recíproca nos termos do art. 86 do Código de Processo Civil.",
        "parcialmente procedente",
    ),
    (
        "Julgo extinto o processo sem resolução do mérito, nos termos do art. 485, inciso IV e VI, do Código de Processo Civil. Indefiro a petição inicial.",
        "extinto sem mérito",
    ),
    (
        "Homologo a desistência manifestada pela parte autora e declaro extinto o feito sem julgamento do mérito com fulcro no art. 51 da Lei 9.099/95.",
        "extinto sem mérito",
    ),
    (
        "Homologo por sentença o acordo celebrado entre as partes para que surta seus efeitos jurídicos, extinguindo o processo com resolução de mérito, art. 487, III, b, do CPC.",
        "acordo",
    ),
    (
        "Homologo a transação extrajudicial entabulada pelas partes. Sem custas e sem honorários, na forma da Lei 9.099/95.",
        "acordo",
    ),
    (
        "Tendo em vista a satisfação integral da obrigação pelo devedor, julgo extinta a execução e o cumprimento de sentença com fulcro no art. 924, II, do CPC.",
        "extinção da execução",
    ),
    (
        "Reconheço a prescrição intercorrente e julgo extinta a presente execução fiscal. Expeça-se alvará de levantamento e arquivem-se os autos.",
        "extinção da execução",
    ),
    (
        "Acordam os Desembargadores em conhecer do recurso de apelação e negar-lhe provimento, mantendo inalterada a sentença recorrida por seus próprios fundamentos.",
        "não provido",
    ),
    (
        "Vistos, relatados e discutidos estes autos, decidem os juízes da Turma Recursal conhecer e negar provimento ao recurso inominado, rejeitando os embargos de declaração.",
        "não provido",
    ),
    (
        "Acordam os integrantes da Câmara Cível, à unanimidade, em conhecer e dar provimento ao recurso de apelação para reformar a sentença.",
        "provido",
    ),
    (
        "Conheço do agravo de instrumento e dou-lhe provimento para conceder a tutela recursal pleiteada pelo agravante.",
        "provido",
    ),
    (
        "Acordam os Desembargadores em conhecer do recurso e dar-lhe parcial provimento apenas para reduzir o quantum indenizatório.",
        "parcialmente provido",
    ),
    (
        "Recurso conhecido e provido em parte para adequar os consectários legais e juros de mora à taxa SELIC.",
        "parcialmente provido",
    ),
    (
        "Diante da intempestividade e deserção, não conheço do recurso interposto e inadmito o recurso extraordinário, negando-lhe seguimento nos termos do art. 1.030 do CPC.",
        "não conhecido",
    ),
    (
        "Presentes a probabilidade do direito e o perigo de dano, defiro a tutela de urgência liminar para determinar a suspensão dos descontos e expedição de mandado de busca e apreensão.",
        "tutela deferida",
    ),
    (
        "Ausentes os requisitos do art. 300 do CPC, indefiro o pedido de tutela provisória de urgência e denego a liminar pleiteada.",
        "tutela indeferida",
    ),
    (
        "Intime-se a parte autora para manifestação em 15 dias sobre a contestação e documentos juntados. Após, dê-se vista ao Ministério Público e voltem os autos conclusos.",
        "despacho de expediente",
    ),
    (
        "Determino o sobrestamento e a suspensão do feito até o julgamento do Tema Repetitivo pelo STJ. Redistribua-se o processo ao juízo competente.",
        "despacho de expediente",
    ),
    (
        "Fica a parte exequente intimada por meio de seu advogado para indicar bens à penhora e apresentar cálculos no cumprimento de sentença.",
        "despacho de expediente",
    ),
    (
        "Homologo, para que produza seus jurídicos e legais efeitos, o projeto de sentença e a decisão leiga elaborada pelo Juiz Leigo, nos termos do art. 40 da Lei 9.099/95.",
        "homologação de decisão leiga",
    ),
]


@dataclass
class FallbackPrediction:
    """Resultado da predição do classificador ML Fallback."""

    category: str
    confidence: float
    rule_id: str | None


class WeakSupervisionOutcomeFallback:
    """Classificador TF-IDF + Random Forest treinado via Supervisão Fraca e Distante."""

    def __init__(self, min_proba: float = 0.40):
        self.min_proba = min_proba
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=2500,
            sublinear_tf=True,
            strip_accents="unicode",
            lowercase=True,
        )
        self.classifier = RandomForestClassifier(
            n_estimators=100,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=1,
        )
        self._is_fitted = False

    def fit_default(self) -> None:
        """Treina o modelo com o corpus semente canônico."""
        texts = [t for t, _ in _CANONICAL_SEED_CORPUS]
        labels = [lbl for _, lbl in _CANONICAL_SEED_CORPUS]
        x_mat = self.vectorizer.fit_transform(texts)
        self.classifier.fit(x_mat, labels)
        self._is_fitted = True

    def fit_from_corpus(
        self,
        texts: list[str],
        labels: list[str],
        confidences: list[float] | None = None,
        min_confidence: float = 0.85,
    ) -> int:
        """Treina combinando o corpus canônico com decisões reais de alta confiança."""
        train_texts = [t for t, _ in _CANONICAL_SEED_CORPUS]
        train_labels = [lbl for _, lbl in _CANONICAL_SEED_CORPUS]

        for idx, (txt, lbl) in enumerate(zip(texts, labels, strict=False)):
            if not txt or not lbl or lbl in {"unknown", "none", ""}:
                continue
            if confidences is not None and idx < len(confidences):
                if confidences[idx] < min_confidence:
                    continue
            snippet = txt[-900:] if len(txt) > 900 else txt
            train_texts.append(snippet)
            train_labels.append(lbl)

        x_mat = self.vectorizer.fit_transform(train_texts)
        self.classifier.fit(x_mat, train_labels)
        self._is_fitted = True
        return len(train_texts)

    def predict(
        self,
        text: str,
        sections: dict[str, str] | None = None,
        macro_categoria: str | None = None,
    ) -> FallbackPrediction:
        """Prediz o desfecho operativo respeitando a restrição de domínio da `macro_categoria`."""
        if not text:
            return FallbackPrediction(category="unknown", confidence=0.0, rule_id=None)

        if not self._is_fitted:
            self.fit_default()

        disp = (sections or {}).get("dispositivo", "")
        tail = text[-800:] if len(text) > 800 else text
        eval_text = f"{disp}\n{tail}".strip()
        if not eval_text:
            return FallbackPrediction(category="unknown", confidence=0.0, rule_id=None)

        x_vec = self.vectorizer.transform([eval_text])
        probas: Any = self.classifier.predict_proba(x_vec)[0]
        classes = [str(c) for c in self.classifier.classes_]

        allowed = ALLOWED_OUTCOMES_BY_MACRO.get((macro_categoria or "").upper())
        best_cat = "unknown"
        best_proba = 0.0

        for cls_name, p in zip(classes, probas, strict=False):
            if allowed is not None and cls_name not in allowed:
                continue
            if float(p) > best_proba:
                best_proba = float(p)
                best_cat = cls_name

        if best_cat != "unknown" and best_proba >= self.min_proba:
            scaled_conf = round(min(0.84, max(0.55, best_proba)), 4)
            return FallbackPrediction(
                category=best_cat,
                confidence=scaled_conf,
                rule_id="ml_rf_tfidf_fallback",
            )

        return FallbackPrediction(category="unknown", confidence=0.0, rule_id=None)
