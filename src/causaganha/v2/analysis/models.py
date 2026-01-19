"""Pydantic models for decision analysis."""

from enum import Enum
import re
from pydantic import BaseModel, Field, field_validator


class Outcome(str, Enum):
    """Possible outcomes of a judicial decision."""
    PROCEDENTE = "procedente"
    IMPROCEDENTE = "improcedente"
    PARCIALMENTE_PROCEDENTE = "parcialmente procedente"
    UNKNOWN = "unknown"  # Fallback


class DecisionType(str, Enum):
    """Types of judicial decisions."""
    SENTENCA = "sentença"
    ACORDAO = "acórdão"
    DECISAO_INTERLOCUTORIA = "decisão interlocutória"
    UNKNOWN = "unknown"


# List of valid Brazilian states
VALID_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
}


class DecisionAnalysis(BaseModel):
    """Structured output from LLM analysis of a judicial decision.

    This model defines exactly what we expect from the AI.
    """

    winner_lawyer_oab: str = Field(
        description="OAB registration number of the winning lawyer (e.g., '5733')",
    )
    winner_lawyer_state: str = Field(
        max_length=2,
        description="State code of winner's OAB registration (e.g., 'RO')",
    )
    winner_party_name: str = Field(description="Full name of the winning party")

    loser_lawyer_oab: str = Field(
        description="OAB registration number of the losing lawyer",
    )
    loser_lawyer_state: str = Field(
        max_length=2,
        description="State code of loser's OAB registration",
    )
    loser_party_name: str = Field(description="Full name of the losing party")

    decision_type: DecisionType = Field(
        description=(
            "Type of decision: 'sentença' (first instance judgment), "
            "'acórdão' (appellate decision), or 'decisão interlocutória' "
            "(interlocutory decision)"
        ),
    )
    outcome: Outcome = Field(
        description=(
            "Outcome of the decision: 'procedente' (granted in full), "
            "'improcedente' (denied), or 'parcialmente procedente' (partially granted)"
        ),
    )

    judge_name: str = Field(
        description="Full name of the judge or rapporteur who issued the decision",
    )

    decision_reasoning: str = Field(
        description=(
            "Brief summary of the judge's main reasoning and legal basis "
            "for the decision (2-3 sentences maximum)"
        ),
    )

    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Confidence level in this analysis (0.0 to 1.0). "
            "Use lower scores if information is unclear or ambiguous."
        ),
    )

    @field_validator("decision_type", "outcome", mode="before")
    @classmethod
    def normalize_enum(cls, v: str) -> str:
        """Normalize enum values to lowercase to handle LLM capitalization."""
        if not v:
            return "unknown"
        return v.lower().strip()

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
        matches = re.findall(r'\b([A-Z]{2})\b', v)
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
