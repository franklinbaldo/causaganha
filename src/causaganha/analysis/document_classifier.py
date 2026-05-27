"""Classifier for document types and procedural stages in judicial decision texts.

Classifies decision texts into:
1. Document Type: despacho, sentença, acórdão, decisão monocrática, decisão interlocutória, etc.
2. Procedural Stage / Context: cumprimento de sentença, apelação, embargos de declaração, agravo de instrumento, etc.
"""

import re
from typing import TypedDict


class ClassificationResult(TypedDict):
    document_type: str
    procedural_class: str
    confidence: float
    matched_keywords: list[str]

class DocumentClassifier:
    """Rule-based classifier for judicial documents."""

    def __init__(self) -> None:
        # Pre-compile regex patterns for efficiency

        # Document Type Rules
        self.doc_rules = {
            "acórdão": [
                re.compile(r"\bacordam\b", re.IGNORECASE),
                re.compile(r"\bacórdão\b", re.IGNORECASE),
                re.compile(r"vistos, relatados e discutidos", re.IGNORECASE),
                re.compile(r"turma recursal", re.IGNORECASE),
                re.compile(r"câmara cível", re.IGNORECASE),
            ],
            "decisão monocrática": [
                re.compile(r"decisão monocrática", re.IGNORECASE),
                re.compile(r"\bmonocraticamente\b", re.IGNORECASE),
                re.compile(r"decido monocraticamente", re.IGNORECASE),
                re.compile(r"nego provimento ao recurso", re.IGNORECASE),
                re.compile(r"dou provimento ao recurso", re.IGNORECASE),
                re.compile(r"provimento ao recurso da parte", re.IGNORECASE),
            ],
            "sentença": [
                re.compile(r"\bsentença\b", re.IGNORECASE),
                re.compile(r"julgo\s+(parcialmente\s+)?procedente", re.IGNORECASE),
                re.compile(r"julgo\s+improcedente", re.IGNORECASE),
                re.compile(r"extingo o processo com resolução do mérito", re.IGNORECASE),
                re.compile(r"extingo o processo sem resolução do mérito", re.IGNORECASE),
                re.compile(r"homologo a transação", re.IGNORECASE),
                re.compile(r"homologo por sentença", re.IGNORECASE),
                re.compile(r"partes transigiram", re.IGNORECASE),
                re.compile(r"\bp\.r\.i\.?\b", re.IGNORECASE),
                re.compile(r"publique-se\.?\s+registre-se", re.IGNORECASE),
            ],
            "decisão interlocutória": [
                re.compile(r"decisão interlocutória", re.IGNORECASE),
                re.compile(r"defiro o pedido de liminar", re.IGNORECASE),
                re.compile(r"defiro a tutela", re.IGNORECASE),
                re.compile(r"indefiro a tutela", re.IGNORECASE),
                re.compile(r"tutela de urgência", re.IGNORECASE),
                re.compile(r"tutela provisória", re.IGNORECASE),
                re.compile(r"concedo a liminar", re.IGNORECASE),
                re.compile(r"indefiro a liminar", re.IGNORECASE),
            ],
            "despacho": [
                re.compile(r"\bdespacho\b", re.IGNORECASE),
                re.compile(r"\bintime-se\b", re.IGNORECASE),
                re.compile(r"\bmanifeste-se\b", re.IGNORECASE),
                re.compile(r"\bdiga a parte\b", re.IGNORECASE),
                re.compile(r"\baguarde-se\b", re.IGNORECASE),
                re.compile(r"\bcite-se\b", re.IGNORECASE),
                re.compile(r"defiro a dilação de prazo", re.IGNORECASE),
                re.compile(r"subam os autos", re.IGNORECASE),
                re.compile(r"remetam-se os autos", re.IGNORECASE),
            ],
        }

        # Procedural Class Rules
        self.class_rules = {
            "cumprimento de sentença": [
                re.compile(r"cumprimento de sentença", re.IGNORECASE),
                re.compile(r"cumprimento da sentença", re.IGNORECASE),
                re.compile(r"cumprimento provisório", re.IGNORECASE),
                re.compile(r"fase de cumprimento", re.IGNORECASE),
                re.compile(r"impugnação ao cumprimento", re.IGNORECASE),
                re.compile(r"\bexequente\b", re.IGNORECASE),
                re.compile(r"\bexecutado\b", re.IGNORECASE),
                re.compile(r"\bpenhora\b", re.IGNORECASE),
                re.compile(r"\bsisbajud\b", re.IGNORECASE),
                re.compile(r"\brenajud\b", re.IGNORECASE),
            ],
            "embargos de declaração": [
                re.compile(r"embargos de declaração", re.IGNORECASE),
                re.compile(r"embargos declaratórios", re.IGNORECASE),
                re.compile(r"\bembargante\b", re.IGNORECASE),
                re.compile(r"\bembargado\b", re.IGNORECASE),
                re.compile(r"rejeito os embargos", re.IGNORECASE),
                re.compile(r"acolho os embargos", re.IGNORECASE),
            ],
            "apelação": [
                re.compile(r"\bapelação\b", re.IGNORECASE),
                re.compile(r"recurso de apelação", re.IGNORECASE),
                re.compile(r"\bapelante\b", re.IGNORECASE),
                re.compile(r"\bapelado\b", re.IGNORECASE),
            ],
            "agravo de instrumento": [
                re.compile(r"agravo de instrumento", re.IGNORECASE),
                re.compile(r"agravo interno", re.IGNORECASE),
                re.compile(r"agravo regimental", re.IGNORECASE),
                re.compile(r"\bagravante\b", re.IGNORECASE),
                re.compile(r"\bagravado\b", re.IGNORECASE),
                re.compile(r"efeito suspensivo", re.IGNORECASE),
            ],
            "execução de título": [
                re.compile(r"execução de título", re.IGNORECASE),
                re.compile(r"execução extrajudicial", re.IGNORECASE),
                re.compile(r"execução de título extrajudicial", re.IGNORECASE),
                re.compile(r"embargos à execução", re.IGNORECASE),
            ],
            "conhecimento": [
                re.compile(r"ação ordinária", re.IGNORECASE),
                re.compile(r"ação declaratória", re.IGNORECASE),
                re.compile(r"ação de cobrança", re.IGNORECASE),
                re.compile(r"ação indenizatória", re.IGNORECASE),
                re.compile(r"ação de obrigação", re.IGNORECASE),
                re.compile(r"ação revisional", re.IGNORECASE),
                re.compile(r"petição inicial", re.IGNORECASE),
                re.compile(r"\bcontestação\b", re.IGNORECASE),
                re.compile(r"\breplica\b", re.IGNORECASE),
            ],
        }

    def classify(self, text: str) -> ClassificationResult:
        """Classify a decision text into document type and procedural class."""
        if not text or not text.strip():
            return {
                "document_type": "outro",
                "procedural_class": "outro",
                "confidence": 0.0,
                "matched_keywords": [],
            }

        matched_keywords: list[str] = []

        # 1. Document Type Classification
        doc_scores: dict[str, int] = {}
        for doc_type, patterns in self.doc_rules.items():
            score = 0
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    score += len(matches)
                    matched_keywords.append(pattern.pattern)
            if score > 0:
                doc_scores[doc_type] = score

        # Determine best document type
        # Check order/priority if multiple match
        if not doc_scores:
            document_type = "outro"
        else:
            # We want to favor acórdão/decisão monocrática over sentença/despacho
            # Let's find the max score
            max_score = max(doc_scores.values())
            best_types = [dt for dt, score in doc_scores.items() if score == max_score]

            # Tie breaking priority
            priority = ["acórdão", "decisão monocrática", "sentença", "decisão interlocutória", "despacho"]
            document_type = "outro"
            for p in priority:
                if p in best_types:
                    document_type = p
                    break
            if document_type == "outro":
                document_type = best_types[0]

        # 2. Procedural Class Classification
        class_scores: dict[str, int] = {}
        for class_name, patterns in self.class_rules.items():
            score = 0
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    score += len(matches)
                    matched_keywords.append(pattern.pattern)
            if score > 0:
                class_scores[class_name] = score

        if not class_scores:
            procedural_class = "outro"
        else:
            # Get the class with the highest score
            procedural_class = max(class_scores, key=class_scores.get) # type: ignore[arg-type]

        # Calculate confidence based on the number of matches
        total_matches = len(matched_keywords)
        confidence = min(1.0, 0.3 + (total_matches * 0.1)) if total_matches > 0 else 0.0

        return {
            "document_type": document_type,
            "procedural_class": procedural_class,
            "confidence": round(confidence, 2),
            "matched_keywords": list(set(matched_keywords)),
        }
