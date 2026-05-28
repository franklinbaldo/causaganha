"""Pydantic models for decision analysis."""

import re
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Outcome(StrEnum):
    """Possible outcomes of a judicial decision."""

    PROCEDENTE = "procedente"
    IMPROCEDENTE = "improcedente"
    PARCIALMENTE_PROCEDENTE = "parcialmente procedente"
    ACORDO = "acordo"
    EXTINTO_SEM_MERITO = "extinto sem mérito"
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
            "'acordo' (settlement), 'extinto sem mérito' (dismissed without prejudice), "
            "or simplified: WIN, LOSS, PARTIAL, SETTLEMENT, UNKNOWN"
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

    # ---------------------------------------------------------------------------
    # Rich extraction fields (LLM only, optional)
    # ---------------------------------------------------------------------------

    fase_processual: str | None = Field(
        default=None,
        description="Fase do processo: 'conhecimento', 'execução', 'recursal', 'cautelar'",
    )
    classe_processual: str | None = Field(
        default=None,
        description="Classe da ação: e.g. 'Procedimento Comum Cível', 'Juizado Especial', "
        "'Execução de Título Extrajudicial', 'Apelação Cível'",
    )
    assunto_principal: str | None = Field(
        default=None,
        description="Assunto jurídico principal: e.g. 'danos morais', 'cobrança', "
        "'rescisão contratual', 'alimentos'",
    )
    valor_causa: float | None = Field(
        default=None,
        description="Valor da causa em reais (float), se mencionado",
    )
    valor_condenacao: float | None = Field(
        default=None,
        description="Valor da condenação em reais (float), se mencionado no dispositivo",
    )
    proposed_regex: str | None = Field(
        default=None,
        description="Padrão regex Python (raw string) que identificaria decisões similares",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Palavras-chave que melhor representam o conteúdo da decisão",
    )
    legal_bases: list[str] = Field(
        default_factory=list,
        description="Normas, artigos, súmulas e temas repetitivos mencionados no texto",
    )
    precedents: dict[str, str] = Field(
        default_factory=dict,
        description="Precedentes citados mapeados para 'confirmado', 'distinto' ou 'ultrapassado'",
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
        if v_upper in ["WIN", "LOSS", "PARTIAL", "SETTLEMENT", "UNKNOWN"]:
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
