"""Situation-based outcome classifier for Brazilian legal decisions.

Two-stage classification:
1. Identify SITUATION (document type, procedural context, parties)
2. Map situation to OUTCOME (WIN/LOSS/PARTIAL)

This models real-world legal reasoning more accurately than direct classification.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Literal

import structlog


logger = structlog.get_logger()

# Outcome type (must always predict - use confidence to indicate uncertainty)
Outcome = Literal["WIN", "LOSS", "PARTIAL"]


class Situation(str, Enum):
    """Legal situation types that can be identified."""

    # First instance decisions
    FIRST_INSTANCE_PROCEDENTE = "first_instance_procedente"
    FIRST_INSTANCE_IMPROCEDENTE = "first_instance_improcedente"
    FIRST_INSTANCE_PARCIAL = "first_instance_parcial"

    # Appeal decisions (INSS appealed)
    APPEAL_INSS_DENIED = "appeal_inss_denied"  # INSS lost appeal → author won
    APPEAL_INSS_GRANTED = "appeal_inss_granted"  # INSS won appeal → author lost
    APPEAL_INSS_PARTIAL = "appeal_inss_partial"

    # Appeal decisions (Author appealed)
    APPEAL_AUTHOR_DENIED = "appeal_author_denied"  # Author lost appeal
    APPEAL_AUTHOR_GRANTED = "appeal_author_granted"  # Author won appeal
    APPEAL_AUTHOR_PARTIAL = "appeal_author_partial"

    # Appeal decisions (generic - need to infer who)
    APPEAL_DENIED_GENERIC = "appeal_denied_generic"
    APPEAL_GRANTED_GENERIC = "appeal_granted_generic"

    # Enforcement proceedings (referencing prior decisions)
    ENFORCEMENT_WIN_REFERENCED = "enforcement_win_referenced"
    ENFORCEMENT_LOSS_REFERENCED = "enforcement_loss_referenced"

    # Mandado de segurança
    MANDADO_GRANTED = "mandado_granted"
    MANDADO_DENIED = "mandado_denied"
    MANDADO_PARTIAL = "mandado_partial"

    # Administrative acts (no judgment)
    ADMINISTRATIVE_ACT = "administrative_act"

    # Unknown/unclear
    UNKNOWN = "unknown"


@dataclass
class SituationIdentification:
    """Result of situation identification."""

    situation: Situation
    confidence: float  # 0.0 to 1.0
    evidence: list[str]  # Phrases/patterns that led to this identification
    parties: dict[str, str | None]  # autor, reu, etc.


@dataclass
class OutcomePrediction:
    """Final prediction with situation context."""

    outcome: Outcome
    confidence: float
    situation: Situation
    reasoning: str
    winner_party: str | None = None
    loser_party: str | None = None


class SituationClassifier:
    """Two-stage classifier: Situation → Outcome mapping."""

    # Situation identification patterns
    SITUATION_PATTERNS = {
        # First instance decisions
        # IMPORTANT: Check IMPROCEDENTE before PROCEDENTE to avoid substring matches
        Situation.FIRST_INSTANCE_IMPROCEDENTE: [
            r"\bjulgo\s+improcedente(?:\s+o\s+pedido)?",
            r"\bimprocedente\s+o\s+pedido",
            r"\bimprocedentes\s+os\s+pedidos",
        ],
        Situation.FIRST_INSTANCE_PARCIAL: [
            r"\bjulgo\s+parcialmente\s+procedente",
            r"\bparcialmente\s+procedente\s+o\s+pedido",
        ],
        Situation.FIRST_INSTANCE_PROCEDENTE: [
            r"\bjulgo\s+procedente(?:\s+o\s+pedido)?",
            r"\bprocedente\s+o\s+pedido",
            r"\bprocedentes\s+os\s+pedidos",
        ],
        # INSS appeals
        Situation.APPEAL_INSS_DENIED: [
            r"negar\s+provimento\s+(?:à|a)\s+apela[çc][ãa]o\s+do\s+inss",
            r"negar\s+provimento\s+ao\s+recurso\s+do\s+inss",
            r"desprovido\s+o\s+recurso\s+do\s+inss",
        ],
        Situation.APPEAL_INSS_GRANTED: [
            r"dar\s+provimento\s+(?:à|a)\s+apela[çc][ãa]o\s+do\s+inss",
            r"dar\s+provimento\s+ao\s+recurso\s+do\s+inss",
            r"provido\s+o\s+recurso\s+do\s+inss",
        ],
        # Author appeals
        Situation.APPEAL_AUTHOR_DENIED: [
            r"negar\s+provimento\s+(?:à|a)\s+apela[çc][ãa]o\s+(?:do|da)\s+autor",
            r"negar\s+provimento\s+(?:à|a)\s+apela[çc][ãa]o\s+(?:do|da)\s+(?:requerente|impetrante)",
            r"desprovido\s+o\s+recurso\s+(?:do|da)\s+autor",
        ],
        Situation.APPEAL_AUTHOR_GRANTED: [
            r"dar\s+provimento\s+(?:à|a)\s+apela[çc][ãa]o\s+(?:do|da)\s+autor",
            r"dar\s+provimento\s+(?:à|a)\s+apela[çc][ãa]o\s+(?:do|da)\s+(?:requerente|impetrante)",
            r"provido\s+o\s+recurso\s+(?:do|da)\s+autor",
        ],
        # Generic appeals
        Situation.APPEAL_DENIED_GENERIC: [
            r"negar\s+provimento\s+(?:ao|à|a)\s+(?:agravo|recurso|apela[çc][ãa]o)",
            r"desprovido\s+o\s+(?:agravo|recurso)",
        ],
        Situation.APPEAL_GRANTED_GENERIC: [
            r"dar\s+provimento\s+(?:ao|à|a)\s+(?:agravo|recurso|apela[çc][ãa]o)",
            r"provido\s+o\s+(?:agravo|recurso)",
        ],
        # Mandado de segurança
        Situation.MANDADO_GRANTED: [
            r"conceder\s+(?:a\s+)?seguran[çc]a",
            r"defiro\s+(?:a\s+)?seguran[çc]a",
            r"mandado\s+de\s+seguran[çc]a\s+(?:é\s+)?concedido",
        ],
        Situation.MANDADO_DENIED: [
            r"denegar\s+(?:a\s+)?seguran[çc]a",
            r"indefiro\s+(?:a\s+)?seguran[çc]a",
            r"mandado\s+de\s+seguran[çc]a\s+(?:é\s+)?denegado",
        ],
        # Administrative acts
        Situation.ADMINISTRATIVE_ACT: [
            r"ato\s+ordinat[óo]rio",
            r"intima[çc][ãa]o\s+realizada",
            r"certid[ãa]o\s+de\s+(?:tr[âa]nsito|publica[çc][ãa]o)",
        ],
    }

    # Situation → Outcome mapping
    SITUATION_OUTCOMES = {
        # First instance (straightforward)
        Situation.FIRST_INSTANCE_PROCEDENTE: ("WIN", 1.0, "First instance: procedente"),
        Situation.FIRST_INSTANCE_IMPROCEDENTE: ("LOSS", 1.0, "First instance: improcedente"),
        Situation.FIRST_INSTANCE_PARCIAL: ("PARTIAL", 1.0, "First instance: parcial"),
        # INSS appeals
        Situation.APPEAL_INSS_DENIED: ("WIN", 0.95, "INSS appeal denied → author wins"),
        Situation.APPEAL_INSS_GRANTED: ("LOSS", 0.95, "INSS appeal granted → author loses"),
        Situation.APPEAL_INSS_PARTIAL: ("PARTIAL", 0.9, "INSS appeal partially granted"),
        # Author appeals
        Situation.APPEAL_AUTHOR_DENIED: ("LOSS", 0.95, "Author appeal denied"),
        Situation.APPEAL_AUTHOR_GRANTED: ("WIN", 0.95, "Author appeal granted"),
        Situation.APPEAL_AUTHOR_PARTIAL: ("PARTIAL", 0.9, "Author appeal partially granted"),
        # Mandado de segurança
        Situation.MANDADO_GRANTED: ("WIN", 0.95, "Mandado de segurança granted"),
        Situation.MANDADO_DENIED: ("LOSS", 0.95, "Mandado de segurança denied"),
        Situation.MANDADO_PARTIAL: ("PARTIAL", 0.9, "Mandado de segurança partial"),
        # Enforcement (references prior decision)
        Situation.ENFORCEMENT_WIN_REFERENCED: ("WIN", 0.85, "Enforcement of winning decision"),
        Situation.ENFORCEMENT_LOSS_REFERENCED: ("LOSS", 0.85, "Enforcement of losing decision"),
        # Administrative (default to WIN with very low confidence)
        Situation.ADMINISTRATIVE_ACT: ("WIN", 0.2, "Administrative act (defaulting to WIN)"),
        # Unknown (default to WIN with very low confidence - most common in dataset)
        Situation.UNKNOWN: ("WIN", 0.3, "Cannot determine situation (defaulting to WIN)"),
    }

    # Party patterns
    PARTY_PATTERNS = {
        "inss": r"inss|instituto\s+nacional\s+do\s+seguro\s+social",
        "autor": r"(?:autor|autora|requerente|impetrante|exequente)",
        "reu": r"(?:r[ée]u|r[ée]|requerido|impetrado|executado)",
        "uniao": r"uni[ãa]o|fazenda\s+p[úu]blica",
    }

    def _extract_parties(self, text: str) -> dict[str, str | None]:
        """Extract party names from text."""
        text_lower = text.lower()
        parties = {}

        if re.search(self.PARTY_PATTERNS["inss"], text_lower):
            parties["reu"] = "INSS"
        elif re.search(self.PARTY_PATTERNS["uniao"], text_lower):
            parties["reu"] = "UNIÃO"

        if re.search(self.PARTY_PATTERNS["autor"], text_lower):
            parties["autor"] = "AUTOR"

        return parties

    def _identify_situation(self, text: str) -> SituationIdentification:
        """Stage 1: Identify the legal situation."""
        text_lower = text.lower()
        parties = self._extract_parties(text)

        # Try each situation pattern
        best_situation = Situation.UNKNOWN
        best_confidence = 0.0
        best_evidence = []

        for situation, patterns in self.SITUATION_PATTERNS.items():
            matches = []
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    matches.append(pattern)

            if matches:
                # More matches = higher confidence
                confidence = min(1.0, len(matches) * 0.4 + 0.6)
                if confidence > best_confidence:
                    best_situation = situation
                    best_confidence = confidence
                    best_evidence = matches

        # Special handling for generic appeals - try to infer who appealed
        if best_situation == Situation.APPEAL_DENIED_GENERIC:
            best_situation, best_confidence = self._infer_appellant_denied(
                text_lower, parties, best_confidence
            )
        elif best_situation == Situation.APPEAL_GRANTED_GENERIC:
            best_situation, best_confidence = self._infer_appellant_granted(
                text_lower, parties, best_confidence
            )

        logger.info(
            "situation_identified",
            situation=best_situation.value,
            confidence=best_confidence,
            num_evidence=len(best_evidence),
        )

        return SituationIdentification(
            situation=best_situation,
            confidence=best_confidence,
            evidence=best_evidence[:3],  # Top 3
            parties=parties,
        )

    def _infer_appellant_denied(
        self, text: str, parties: dict, base_confidence: float
    ) -> tuple[Situation, float]:
        """Infer who appealed when appeal was denied (generic pattern matched)."""
        # Look for context clues about who appealed

        # Check for explicit appellant patterns (including "agravante" for agravo de instrumento)
        # Author/plaintiff as appellant
        if re.search(r"(?:apelante|agravante|recorrente)\s+(?:autor|requerente|impetrante)", text):
            return Situation.APPEAL_AUTHOR_DENIED, base_confidence * 0.9

        # INSS as appellant
        if re.search(r"(?:apelante|agravante|recorrente)\s+inss", text):
            return Situation.APPEAL_INSS_DENIED, base_confidence * 0.9

        # Check for appellee patterns (opposite inference)
        # If author is appellee, INSS is appellant
        if re.search(r"(?:apelad[oa]|agravad[oa])\s+(?:autor|requerente)", text):
            return Situation.APPEAL_INSS_DENIED, base_confidence * 0.85

        # If INSS is appellee, author is appellant (KEY PATTERN for agravo cases)
        if re.search(r"(?:apelad[oa]|agravad[oa]).*?inss", text, re.DOTALL):
            return Situation.APPEAL_AUTHOR_DENIED, base_confidence * 0.8
        if re.search(r"inss.*?(?:apelad[oa]|agravad[oa])", text, re.DOTALL):
            return Situation.APPEAL_AUTHOR_DENIED, base_confidence * 0.75

        # REMOVED: Default assumption that INSS appealed (was causing errors)
        # Instead, keep as generic with lower confidence
        return Situation.APPEAL_DENIED_GENERIC, base_confidence * 0.5

    def _infer_appellant_granted(
        self, text: str, parties: dict, base_confidence: float
    ) -> tuple[Situation, float]:
        """Infer who appealed when appeal was granted (generic pattern matched)."""
        # Check for explicit appellant patterns (including "agravante" for agravo de instrumento)
        # Author/plaintiff as appellant
        if re.search(r"(?:apelante|agravante|recorrente)\s+(?:autor|requerente|impetrante)", text):
            return Situation.APPEAL_AUTHOR_GRANTED, base_confidence * 0.9

        # INSS as appellant
        if re.search(r"(?:apelante|agravante|recorrente)\s+inss", text):
            return Situation.APPEAL_INSS_GRANTED, base_confidence * 0.9

        # Check for appellee patterns (opposite inference)
        # If author is appellee, INSS is appellant
        if re.search(r"(?:apelad[oa]|agravad[oa])\s+(?:autor|requerente)", text):
            return Situation.APPEAL_INSS_GRANTED, base_confidence * 0.85

        # If INSS is appellee, author is appellant (KEY PATTERN for agravo cases)
        if re.search(r"(?:apelad[oa]|agravad[oa]).*?inss", text, re.DOTALL):
            return Situation.APPEAL_AUTHOR_GRANTED, base_confidence * 0.8
        if re.search(r"inss.*?(?:apelad[oa]|agravad[oa])", text, re.DOTALL):
            return Situation.APPEAL_AUTHOR_GRANTED, base_confidence * 0.75

        # REMOVED: Default assumption that INSS appealed (was causing errors)
        # Instead, keep as generic with lower confidence
        return Situation.APPEAL_GRANTED_GENERIC, base_confidence * 0.5

    def predict(self, intimacao_text: str, dependencies: dict | None = None) -> OutcomePrediction:
        """Two-stage prediction: Situation → Outcome.

        Args:
            intimacao_text: Text of legal decision
            dependencies: Optional context

        Returns:
            OutcomePrediction with situation-based reasoning
        """
        if dependencies is None:
            dependencies = {}

        # Stage 1: Identify situation
        situation_id = self._identify_situation(intimacao_text)

        # Stage 2: Map situation to outcome
        if situation_id.situation in self.SITUATION_OUTCOMES:
            outcome, base_conf, reasoning = self.SITUATION_OUTCOMES[situation_id.situation]
            # Final confidence is product of situation confidence and base mapping confidence
            final_confidence = situation_id.confidence * base_conf
        else:
            # Handle generic appeals with lower confidence
            if situation_id.situation == Situation.APPEAL_DENIED_GENERIC:
                # Default: assume INSS appealed (more common)
                outcome = "WIN"
                final_confidence = situation_id.confidence * 0.5
                reasoning = "Generic appeal denied (assumed INSS appellant)"
            elif situation_id.situation == Situation.APPEAL_GRANTED_GENERIC:
                outcome = "LOSS"
                final_confidence = situation_id.confidence * 0.5
                reasoning = "Generic appeal granted (assumed INSS appellant)"
            else:
                # Default to WIN (most common) with very low confidence
                outcome = "WIN"
                final_confidence = 0.3
                reasoning = "Unknown situation (defaulting to WIN - most common outcome)"

        # Determine winner/loser
        winner_party = None
        loser_party = None
        if outcome == "WIN":
            winner_party = situation_id.parties.get("autor", "AUTOR")
            loser_party = situation_id.parties.get("reu", "RÉU")
        elif outcome == "LOSS":
            winner_party = situation_id.parties.get("reu", "RÉU")
            loser_party = situation_id.parties.get("autor", "AUTOR")

        logger.info(
            "outcome_predicted",
            situation=situation_id.situation.value,
            outcome=outcome,
            confidence=final_confidence,
        )

        return OutcomePrediction(
            outcome=outcome,
            confidence=final_confidence,
            situation=situation_id.situation,
            reasoning=f"{reasoning} (situation: {situation_id.situation.value}, conf={final_confidence:.2f})",
            winner_party=winner_party,
            loser_party=loser_party,
        )


def predict_outcome_by_situation(
    intimacao_text: str,
    dependencies: dict | None = None,
) -> OutcomePrediction:
    """Pure function: Predict outcome using situation-based classification.

    Two-stage process:
    1. Identify legal situation (first instance, appeal, enforcement, etc.)
    2. Map situation to outcome (WIN/LOSS/PARTIAL)

    Args:
        intimacao_text: Text of legal decision
        dependencies: Optional context (prior decisions, party info, etc.)

    Returns:
        OutcomePrediction with situation-based reasoning

    Example:
        >>> prediction = predict_outcome_by_situation(
        ...     "NEGAR PROVIMENTO À APELAÇÃO DO INSS..."
        ... )
        >>> print(prediction.situation)  # "appeal_inss_denied"
        >>> print(prediction.outcome)    # "WIN"
        >>> print(prediction.confidence) # 0.90
    """
    classifier = SituationClassifier()
    return classifier.predict(intimacao_text, dependencies)
