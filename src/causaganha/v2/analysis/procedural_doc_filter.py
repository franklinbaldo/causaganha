"""Procedural document filter to identify non-merit decisions.

Based on analysis of 500 labeled documents where 85% were procedural orders:
- ATO ORDINATORIO: Schedule medical exams, request documents
- DESPACHO: Simple procedural orders
- No WIN/LOSS outcomes (not useful for lawyer ratings)

This filter saves resources by skipping these documents before expensive analysis.
"""

import html
import re
from dataclasses import dataclass
from typing import Literal

import structlog

logger = structlog.get_logger()


def clean_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities.

    Args:
        text: HTML text with tags and entities

    Returns:
        Clean text with tags removed and entities decoded

    Example:
        >>> clean_html("<p>ATO ORDINAT&Oacute;RIO</p>")
        'ATO ORDINATÓRIO'
    """
    # Decode HTML entities (&Oacute; → Ó, &ccedil; → ç)
    text = html.unescape(text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()

DocumentType = Literal["MERIT_DECISION", "PROCEDURAL_ORDER", "SEALED", "UNKNOWN"]


@dataclass
class DocumentClassification:
    """Classification result for a legal document."""

    doc_type: DocumentType
    confidence: float  # 0.0 to 1.0
    reasoning: str
    should_analyze: bool  # False for procedural docs


class ProceduralDocumentFilter:
    """Fast classifier to identify procedural documents vs. merit decisions.

    This is a heuristic-based filter designed to quickly identify documents
    that don't contain judicial outcomes (WIN/LOSS), saving compute resources.

    Based on patterns from 427 procedural documents labeled by subagents:
    - 85% of DJEN documents are procedural orders
    - Common types: ATO ORDINATORIO, DESPACHO, INTIMACAO
    - Keywords: "intimar", "marcar perícia", "apresentar documentos"
    - No outcome phrases: "julgo procedente", "dar provimento", etc.
    """

    def __init__(self):
        """Initialize procedural document filter with pattern matching."""

        # Patterns indicating PROCEDURAL ORDER (should skip)
        self.procedural_patterns = [
            # Explicit document type declarations
            r"\bATO\s+ORDINAT[OÓ]RIO\b",
            r"\bDESPACHO\b.*\bINTIMA[ÇC][ÃA]O\b",
            r"\bINTIMA[ÇC][ÃA]O\s+SIMPLES\b",

            # Procedural actions (scheduling, requesting)
            r"\bintim[oa](?:-se)?\s+(?:as\s+partes|o\s+autor|o\s+r[ée]u)\b",
            r"\bmarcar\s+per[íi]cia\b",
            r"\bagendar\s+per[íi]cia\b",
            r"\bdesignar\s+per[íi]cia\b",
            r"\bapresentar\s+(?:documentos|c[óo]pia|comprovante)",
            r"\bjuntar\s+aos\s+autos\b",
            r"\btrazer\s+aos\s+autos\b",
            r"\bmanifesta[çc][ãa]o\s+em\s+\d+\s+dias\b",
            r"\bprazo\s+de\s+\d+\s+dias?\s+para\b",

            # Medical examination scheduling (very common in dataset)
            r"\bpara\s+realiza[çc][ãa]o\s+de\s+per[íi]cia\b",
            r"\bexame\s+(?:m[ée]dico|pericial)\b",
            r"\bavalia[çc][ãa]o\s+(?:m[ée]dica|pericial)\b",

            # Document requests
            r"\bencaminhar\s+(?:documentos|c[óo]pias)\b",
            r"\bprovidenciar\s+a\s+juntada\b",
            r"\bapresentar\s+no\s+prazo\b",
        ]

        # Patterns indicating MERIT DECISION (should analyze)
        self.merit_patterns = [
            # Outcome phrases
            r"\bjulgo\s+(?:procedente|improcedente|parcialmente)",
            r"\b(?:dar|negar)\s+provimento\b",
            r"\b(?:conhecido|provido|desprovido|reformada?|mantid[oa])\b.*\bapela[çc][ãa]o\b",

            # Decision types
            r"\bSENTEN[ÇC]A\b",
            r"\bAC[ÓO]RD[ÃA]O\b",
            r"\bDECIS[ÃA]O\s+MONOCR[ÁA]TICA\b",

            # Verdict language
            r"\bcondenar\s+(?:o\s+r[ée]u|a\s+pagar)\b",
            r"\babsolver\s+o\s+r[ée]u\b",
            r"\bextinguir?\s+(?:o\s+)?processo\s+(?:com|sem)\s+(?:resolu[çc][ãa]o\s+de\s+)?m[ée]rito\b",
        ]

        # Sealed/Secret documents
        self.sealed_patterns = [
            r"\bsigilo(?:so|sa)?\b",
            r"\bsegredo\s+de\s+justi[çc]a\b",
            r"\bacesso\s+restrito\b",
        ]

        # Compile all patterns
        self.procedural_regex = re.compile(
            "|".join(self.procedural_patterns),
            re.IGNORECASE | re.UNICODE,
        )
        self.merit_regex = re.compile(
            "|".join(self.merit_patterns),
            re.IGNORECASE | re.UNICODE,
        )
        self.sealed_regex = re.compile(
            "|".join(self.sealed_patterns),
            re.IGNORECASE | re.UNICODE,
        )

    def classify(self, texto: str) -> DocumentClassification:
        """Classify document as procedural order vs. merit decision.

        Args:
            texto: Document text to classify (may contain HTML)

        Returns:
            DocumentClassification with type, confidence, and whether to analyze

        Logic:
            1. Clean HTML tags and entities
            2. Check for sealed documents (highest priority)
            3. Check for strong merit indicators (SENTENÇA, ACÓRDÃO, outcome phrases)
            4. Check for procedural indicators (intimação, marcar perícia)
            5. Use heuristics if patterns unclear
        """
        if not texto or len(texto.strip()) < 50:
            return DocumentClassification(
                doc_type="UNKNOWN",
                confidence=1.0,
                reasoning="Empty or too short (< 50 chars)",
                should_analyze=False,
            )

        # Clean HTML and entities
        texto_clean = clean_html(texto)
        texto_lower = texto_clean.lower()

        # 1. Check for sealed documents
        if self.sealed_regex.search(texto_clean):
            return DocumentClassification(
                doc_type="SEALED",
                confidence=0.95,
                reasoning="Contains 'sigiloso' or 'segredo de justiça'",
                should_analyze=False,
            )

        # 2. Count pattern matches
        merit_matches = len(self.merit_regex.findall(texto_clean))
        procedural_matches = len(self.procedural_regex.findall(texto_clean))

        logger.debug(
            "document_classification",
            merit_matches=merit_matches,
            procedural_matches=procedural_matches,
            text_length=len(texto_clean),
        )

        # 3. Strong merit indicators (high confidence)
        if merit_matches >= 2 and procedural_matches == 0:
            return DocumentClassification(
                doc_type="MERIT_DECISION",
                confidence=0.9,
                reasoning=f"Strong merit indicators ({merit_matches} matches)",
                should_analyze=True,
            )

        # 4. Strong procedural indicators
        if procedural_matches >= 2 and merit_matches == 0:
            return DocumentClassification(
                doc_type="PROCEDURAL_ORDER",
                confidence=0.85,
                reasoning=f"Strong procedural indicators ({procedural_matches} matches)",
                should_analyze=False,
            )

        # 5. Merit wins if both present (likely appeal decision with procedural language)
        if merit_matches > procedural_matches:
            confidence = 0.7 + (0.2 * min(merit_matches - procedural_matches, 2) / 2)
            return DocumentClassification(
                doc_type="MERIT_DECISION",
                confidence=confidence,
                reasoning=f"Merit patterns dominate ({merit_matches} vs {procedural_matches})",
                should_analyze=True,
            )

        # 6. Procedural wins
        if procedural_matches > merit_matches:
            confidence = 0.7 + (0.15 * min(procedural_matches - merit_matches, 2) / 2)
            return DocumentClassification(
                doc_type="PROCEDURAL_ORDER",
                confidence=confidence,
                reasoning=f"Procedural patterns dominate ({procedural_matches} vs {merit_matches})",
                should_analyze=False,
            )

        # 7. Length heuristic (procedural orders tend to be shorter)
        if len(texto_clean) < 800:
            return DocumentClassification(
                doc_type="PROCEDURAL_ORDER",
                confidence=0.6,
                reasoning="Short document (< 800 chars), likely procedural",
                should_analyze=False,
            )

        # 8. Unknown - analyze to be safe
        return DocumentClassification(
            doc_type="UNKNOWN",
            confidence=0.5,
            reasoning="Unclear patterns, defaulting to analyze",
            should_analyze=True,
        )


def should_analyze_document(texto: str) -> bool:
    """Convenience function to quickly check if document should be analyzed.

    Args:
        texto: Document text

    Returns:
        True if document should be analyzed (merit decision), False if procedural

    Example:
        >>> if should_analyze_document(texto):
        >>>     result = await analyzer.analyze(intimation_id, texto)
    """
    filter = ProceduralDocumentFilter()
    classification = filter.classify(texto)
    return classification.should_analyze
