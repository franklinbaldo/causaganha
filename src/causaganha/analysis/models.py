"""Pydantic models for decision analysis."""

import re
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Outcome(StrEnum):
    """Possible outcomes of a judicial decision."""

    PROCEDENTE = "procedente"
    IMPROCEDENTE = "improcedente"
    PARCIALMENTE_PROCEDENTE = "parcialmente procedente"
    UNKNOWN = "unknown"  # Fallback


class DecisionType(StrEnum):
    """Types of judicial decisions."""

    SENTENCA = "sentença"
    ACORDAO = "acórdão"
    DECISAO_INTERLOCUTORIA = "decisão interlocutória"
    UNKNOWN = "unknown"


# List of valid Brazilian states
VALID_STATES = {
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
}


class DecisionAnalysis(BaseModel):
    """Structured output from LLM or RAG analysis of a judicial decision.

    This model defines exactly what we expect from analysis.
    Some fields are optional to support both LLM (full extraction) and
    RAG (outcome classification only) analysis methods.
    """

    # Core identification
    intimation_id: int = Field(default=0, description="Intimation ID being analyzed")

    # Lawyer information (optional for RAG analysis)
    winner_lawyer_oab: str | None = Field(
        default=None,
        description="OAB registration number of the winning lawyer (e.g., '5733')",
    )
    winner_lawyer_state: str | None = Field(
        default=None,
        max_length=2,
        description="State code of winner's OAB registration (e.g., 'RO')",
    )
    winner_party_name: str | None = Field(
        default=None,
        description="Full name of the winning party",
    )

    loser_lawyer_oab: str | None = Field(
        default=None,
        description="OAB registration number of the losing lawyer",
    )
    loser_lawyer_state: str | None = Field(
        default=None,
        max_length=2,
        description="State code of loser's OAB registration",
    )
    loser_party_name: str | None = Field(
        default=None,
        description="Full name of the losing party",
    )

    # Decision classification (required)
    decision_type: DecisionType | str = Field(
        description=(
            "Type of decision: 'sentença' (first instance judgment), "
            "'acórdão' (appellate decision), or 'decisão interlocutória' "
            "(interlocutory decision)"
        ),
    )
    outcome: Outcome | str = Field(
        description=(
            "Outcome of the decision: 'procedente' (granted in full), "
            "'improcedente' (denied), 'parcialmente procedente' (partially granted), "
            "or simplified: WIN, LOSS, PARTIAL, UNKNOWN"
        ),
    )

    # Optional metadata
    judge_name: str | None = Field(
        default=None,
        description="Full name of the judge or rapporteur who issued the decision",
    )

    decision_reasoning: str | None = Field(
        default=None,
        description=(
            "Brief summary of the judge's main reasoning and legal basis "
            "for the decision (2-3 sentences maximum)"
        ),
    )

    # Simple outcome flag
    plaintiff_won: bool = Field(
        default=False,
        description="True if plaintiff/autor won, False otherwise",
    )

    # Summary
    summary: str | None = Field(
        default=None,
        description="Brief summary of the analysis",
    )

    # Confidence score (required)
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Confidence level in this analysis (0.0 to 1.0). "
            "Use lower scores if information is unclear or ambiguous."
        ),
    )

    # Analysis method tracking
    analysis_method: str = Field(
        default="llm",
        description="Method used: 'llm', 'rag', 'hybrid', or 'rag_low_confidence'",
    )

    # RAG-specific tracking
    rag_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score from RAG analysis (if RAG was used)",
    )

    rag_votes: dict[str, int] | None = Field(
        default=None,
        description="Vote distribution from k-NN (if RAG was used)",
    )

    @field_validator("decision_type", "outcome", mode="before")
    @classmethod
    def normalize_enum(cls, v: str) -> str:
        """Normalize enum values to handle both LLM (Portuguese) and RAG (English)."""
        if not v:
            return "unknown"

        v_stripped = v.strip()
        v_upper = v_stripped.upper()

        # Preserve RAG's simplified English terms (uppercase)
        if v_upper in ["WIN", "LOSS", "PARTIAL", "UNKNOWN"]:
            return v_upper

        # Normalize LLM's Portuguese terms to lowercase
        return v_stripped.lower()

    @field_validator("winner_lawyer_state", "loser_lawyer_state", mode="before")
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Validate and normalize state codes."""
        if not v:
            return "RO"  # Default fallback

        v = v.upper().strip()

        # If it's a valid 2-letter code, return it
        if v in VALID_STATES:
            return v

        # Try to extract 2-letter state codes using regex boundaries
        # Look for "OAB/SP", "OAB-SP", " SP " etc.
        # This prevents matching "AL" inside "INVALID"
        matches = re.findall(r"\b([A-Z]{2})\b", v)
        for match in matches:
            if match in VALID_STATES:
                return match

        # Fallback to RO
        return "RO"

    @field_validator("winner_lawyer_oab", "loser_lawyer_oab", mode="before")
    @classmethod
    def clean_oab(cls, v: str) -> str:
        """Clean OAB number. Returns only digits."""
        if not v:
            return "00000"
        # Extract all digits
        digits = "".join(filter(str.isdigit, v))
        if not digits:
            return "00000"
        return digits
