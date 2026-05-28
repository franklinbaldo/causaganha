"""Zero-cost deterministic keyword classifier for judicial outcomes.

Runs before the RAG and LLM layers — no API calls, no embeddings, ~0ms.
Extracts the dispositivo (operative section) of a decision and applies
compiled regex patterns to determine the outcome.

Confidence levels:
    ≥ 0.85  High — caller can skip RAG and LLM entirely
    0.60-0.84  Medium — skip LLM but confirm with RAG
    < 0.60  Low — fall through to RAG

Pattern design follows the taxonomy of real Brazilian judicial decisions
collected from experiments/ samples (sentença, acórdão, decisão monocrática).
Negation handling: "não" within 4 tokens before a verb cancels the match.
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Dispositivo extraction
# ---------------------------------------------------------------------------

_DISPOSITIVO_RE = re.compile(
    r"(?:ante\s+o\s+exposto|posto\s+isso|isso\s+posto|"
    r"diante\s+do\s+exposto|pelo\s+exposto|em\s+face\s+do\s+exposto|"
    r"por\s+tais\s+fundamentos|nestes\s+termos|em\s+conclus[ãa]o|"
    r"pelo\s+que\s+exposto|em\s+vista\s+do\s+exposto)",
    re.IGNORECASE,
)

_DISPOSITIVO_MAX_CHARS = 2000

# ---------------------------------------------------------------------------
# Negation detector
# Matches "não" followed by up to 3 optional words immediately before the
# position being tested (right-anchored, no newline crossing).
# ---------------------------------------------------------------------------

_NEGATION_RE = re.compile(
    r"\bnão\s+(?:\w+\s+){0,3}\s*$",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Outcome patterns: (compiled_regex, base_confidence)
#
# base_confidence when matched in full text.
# Dispositivo match gets +0.10 boost (capped at 1.0).
# Two or more patterns agreeing → +0.07 boost (capped at 1.0).
#
# Ambiguous patterns (dou/nego provimento without polarity context) use
# lower base_confidence so that RAG/LLM can override when needed.
# ---------------------------------------------------------------------------

_OUTCOME_PATTERNS: dict[str, list[tuple[re.Pattern[str], float]]] = {
    "procedente": [
        # Negative lookahead: "julgo procedente em parte" → parcialmente procedente
        (re.compile(r"\bjulgo\s+procedentes?\b(?!\s+em\s+parte)", re.IGNORECASE), 0.90),
        (re.compile(r"\bacolho\s+integralmente\b", re.IGNORECASE), 0.88),
        (re.compile(r"\bprocedente\s+(?:a\s+)?(?:ação|pedido|pretensão)\b", re.IGNORECASE), 0.86),
        (re.compile(r"\bcondeno\s+o\s+r[eé]u\b", re.IGNORECASE), 0.82),
        (re.compile(r"\bdefiro\s+o\s+pedido\b", re.IGNORECASE), 0.60),
        (re.compile(r"\bacolho\s+o\s+pedido\b", re.IGNORECASE), 0.60),
        # Appeal-specific (conjugated + infinitive): ambiguous without polarity context
        (re.compile(r"\bdou\s+(?:integral\s+)?provimento\b", re.IGNORECASE), 0.62),
        (re.compile(r"\bdar\s+(?:integral\s+)?provimento\b", re.IGNORECASE), 0.62),
        (re.compile(r"\breforma[-\s]se?\s+a\s+senten[çc]a\b", re.IGNORECASE), 0.62),
    ],
    "improcedente": [
        (re.compile(r"\bjulgo\s+improcedentes?\b", re.IGNORECASE), 0.90),
        (re.compile(r"\brejeito\s+o\s+pedido\b", re.IGNORECASE), 0.87),
        (re.compile(r"\bnego\s+provimento\b", re.IGNORECASE), 0.70),  # appeal-ambiguous
        (re.compile(r"\bneg[ao]\s+provimento\b", re.IGNORECASE), 0.70),
        (re.compile(r"\bdenego\b", re.IGNORECASE), 0.85),
        (re.compile(r"\binadmito\b", re.IGNORECASE), 0.80),
        (re.compile(r"\bimprocedente\s+(?:a\s+)?(?:ação|pedido)\b", re.IGNORECASE), 0.86),
        # Maintaining first-instance when defendant appealed
        (re.compile(r"\bmantenho\s+a\s+senten[çc]a\b", re.IGNORECASE), 0.60),
    ],
    "parcialmente procedente": [
        (re.compile(r"\bjulgo\s+parcialmente\s+procedentes?\b", re.IGNORECASE), 0.92),
        (re.compile(r"\bparcialmente\s+procedente\b", re.IGNORECASE), 0.90),
        (re.compile(r"\bprocedente\s+em\s+parte\b", re.IGNORECASE), 0.88),
        (re.compile(r"\bprocedência\s+parcial\b", re.IGNORECASE), 0.87),
        # Conjugated and infinitive forms for appeals
        (re.compile(r"\bdou\s+parcial\s+provimento\b", re.IGNORECASE), 0.86),
        (re.compile(r"\bdar\s+parcial\s+provimento\b", re.IGNORECASE), 0.86),
        (re.compile(r"\bdefiro\s+(?:em\s+)?parte\b", re.IGNORECASE), 0.60),
        (re.compile(r"\bacolho\s+(?:em\s+)?parte\b", re.IGNORECASE), 0.60),
        (re.compile(r"\bdefiro\s+parcialmente\b", re.IGNORECASE), 0.60),
    ],
    "acordo": [
        (re.compile(r"\bhomologo\s+por\s+senten[çc]a\s+o\s+acordo\b", re.IGNORECASE), 0.95),
        (re.compile(r"\bhomologo\s+(?:o\s+)?acordo\b", re.IGNORECASE), 0.92),
        (re.compile(r"\bhomologo\s+a\s+transação\b", re.IGNORECASE), 0.92),
        (re.compile(r"\bhomologo\s+a\s+avença\b", re.IGNORECASE), 0.92),
        (re.compile(r"\bhomologo\s+a\s+composi[çc][ãa]o\b", re.IGNORECASE), 0.92),
        (re.compile(
            r"\bconcilia[çc][ãa]o\s+(?:entre\s+as\s+partes|realizada|homologada)\b",
            re.IGNORECASE,
        ), 0.60),
        (re.compile(r"\bas\s+partes\s+transigiram\b", re.IGNORECASE), 0.90),
        (re.compile(r"\bas\s+partes\s+chegaram\s+a\s+acordo\b", re.IGNORECASE), 0.88),
        (re.compile(r"\bhomologo\s+o\s+acordo\s+firmado\b", re.IGNORECASE), 0.93),
    ],
    "extinto sem mérito": [
        (re.compile(r"\bextingo\s+o\s+processo\s+sem\s+resolu[çc][ãa]o\b", re.IGNORECASE), 0.93),
        (re.compile(r"\bextinto\s+sem\s+(?:julgamento\s+do\s+)?m[eé]rito\b", re.IGNORECASE), 0.90),
        (re.compile(r"\bjulgo\s+extinto\s+(?:o\s+processo\s+)?sem\b", re.IGNORECASE), 0.88),
        (re.compile(r"\bpronuncio\s+a\s+decad[êe]ncia\b", re.IGNORECASE), 0.90),
        (re.compile(r"\bpronuncio\s+a\s+prescri[çc][ãa]o\b", re.IGNORECASE), 0.90),
        (re.compile(r"\breconhe[çc]o\s+a\s+prescri[çc][ãa]o\b", re.IGNORECASE), 0.90),
        (re.compile(r"\bcar[êe]ncia\s+de\s+a[çc][ãa]o\b", re.IGNORECASE), 0.87),
        (re.compile(r"\bfalta\s+de\s+interesse\s+de\s+agir\b", re.IGNORECASE), 0.87),
        (re.compile(r"\bilegitimidade\s+(?:ativa|passiva|de\s+parte)\b", re.IGNORECASE), 0.82),
        (re.compile(r"\bnão\s+conheço\s+do\b", re.IGNORECASE), 0.85),
    ],
    "unknown": [
        (re.compile(r"\bcite-se\b", re.IGNORECASE), 0.80),
        (re.compile(r"\bintime-se\b", re.IGNORECASE), 0.80),
        (re.compile(r"\bmanifeste-se\b", re.IGNORECASE), 0.75),
        (re.compile(r"\baguarde-se\b", re.IGNORECASE), 0.72),
        (re.compile(r"\babr[ao]\s+(?:-?se\s+)?vista\b", re.IGNORECASE), 0.72),
        (re.compile(r"\bdecis[ãa]o\s+interlocut[oó]ria\b", re.IGNORECASE), 0.85),
        (re.compile(r"\bdespacho\b", re.IGNORECASE), 0.70),
        (re.compile(r"\bdetermino\s+a\s+intimação\b", re.IGNORECASE), 0.75),
    ],
}

# Confidence boost when 2+ patterns agree on same outcome
_MULTI_MATCH_BOOST = 0.07
_MULTI_MATCH_MIN = 2  # minimum number of matching patterns to trigger boost

# Confidence boost when match is inside the dispositivo
_DISPOSITIVO_BOOST = 0.10


class KeywordClassifier:
    """Deterministic, zero-cost judicial outcome classifier.

    Uses compiled regex patterns applied to the dispositivo section
    (or full text when no dispositivo marker is found). Handles
    negation so "não julgo procedente" is not counted as WIN.
    """

    def extract_dispositivo(self, text: str) -> str | None:
        """Return the operative section of a judicial decision.

        Searches for standard Brazilian dispositivo markers and returns
        the text from the first match, capped at _DISPOSITIVO_MAX_CHARS.
        Returns None if no marker found.
        """
        m = _DISPOSITIVO_RE.search(text)
        if m is None:
            return None
        return text[m.start() : m.start() + _DISPOSITIVO_MAX_CHARS]

    def _match_no_negation(self, pattern: re.Pattern[str], text: str) -> bool:
        """Return True if pattern matches text and the match is not negated.

        Negation: "não" within 4 words immediately before the match start.
        """
        for m in pattern.finditer(text):
            window_start = max(0, m.start() - 60)
            preceding = text[window_start : m.start()]
            if not _NEGATION_RE.search(preceding):
                return True
        return False

    def _score_outcome(
        self,
        outcome: str,
        full_text: str,
        dispositivo: str | None,
    ) -> float:
        """Return confidence score for a given outcome in this text."""
        matched_confidences: list[float] = []

        for pattern, base_conf in _OUTCOME_PATTERNS[outcome]:
            if dispositivo and self._match_no_negation(pattern, dispositivo):
                matched_confidences.append(min(1.0, base_conf + _DISPOSITIVO_BOOST))
            elif self._match_no_negation(pattern, full_text):
                matched_confidences.append(base_conf)

        if not matched_confidences:
            return 0.0

        best = max(matched_confidences)
        if len(matched_confidences) >= _MULTI_MATCH_MIN:
            best = min(1.0, best + _MULTI_MATCH_BOOST)
        return best

    def classify(self, text: str) -> tuple[str, float]:
        """Classify a judicial decision text.

        Args:
            text: Full decision text (or any substring).

        Returns:
            (outcome, confidence) where outcome is one of the canonical
            OUTCOME_KEYS and confidence is in [0.0, 1.0].
            Returns ("unknown", 0.0) when no pattern matches.
        """
        dispositivo = self.extract_dispositivo(text)

        scores = {
            outcome: self._score_outcome(outcome, text, dispositivo)
            for outcome in _OUTCOME_PATTERNS
        }

        best_outcome = max(scores, key=scores.__getitem__)
        best_score = scores[best_outcome]

        if best_score == 0.0:
            return "unknown", 0.0
        return best_outcome, best_score

    def classify_with_dispositivo(
        self,
        text: str,
    ) -> tuple[str, float, str | None]:
        """Classify and also return the extracted dispositivo section.

        Returns:
            (outcome, confidence, dispositivo_text)
        """
        dispositivo = self.extract_dispositivo(text)
        scores = {
            outcome: self._score_outcome(outcome, text, dispositivo)
            for outcome in _OUTCOME_PATTERNS
        }
        best_outcome = max(scores, key=scores.__getitem__)
        best_score = scores[best_outcome]

        if best_score == 0.0:
            return "unknown", 0.0, dispositivo
        return best_outcome, best_score, dispositivo
