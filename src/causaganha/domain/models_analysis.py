from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class Outcome(str, Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class DecisionAnalysis(BaseModel):
    outcome: Outcome = Field(..., description="The outcome of the case.")
    summary: str = Field(..., description="A brief summary of the decision.")
    judge_name: str | None = Field(
        None, description="The name of the judge who signed the decision."
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0."
    )

    # Detailed fields for scoring
    winner_lawyer_oab: str | None = Field(
        None,
        description=(
            "OAB number of the winning lawyer. "
            "If the lawyer is from Procuradoria/AGU and no OAB is listed, use a synthetic identifier like: "
            "'PROCURADORIA-FEDERAL-RO', 'PROCURADORIA-MUNICIPAL-ARIQUEMES-RO', 'PGE-RO', etc. "
            "ALWAYS provide this field when there is a lawyer/procuradoria representing the winning party."
        )
    )
    winner_lawyer_state: str | None = Field(None, description="State of the winning lawyer OAB (e.g., 'RO', 'SP').")
    winner_party_name: str | None = Field(None, description="Name of the winning party.")

    loser_lawyer_oab: str | None = Field(
        None,
        description=(
            "OAB number of the losing lawyer. "
            "If the lawyer is from Procuradoria/AGU and no OAB is listed, use a synthetic identifier like: "
            "'PROCURADORIA-FEDERAL-RO', 'PROCURADORIA-MUNICIPAL-ARIQUEMES-RO', 'PGE-RO', etc. "
            "ALWAYS provide this field when there is a lawyer/procuradoria representing the losing party."
        )
    )
    loser_lawyer_state: str | None = Field(None, description="State of the losing lawyer OAB (e.g., 'RO', 'SP').")
    loser_party_name: str | None = Field(None, description="Name of the losing party.")

    decision_type: str | None = Field(
        None, description="Type of decision (e.g., Sentença, Acórdão)."
    )
    decision_reasoning: str | None = Field(None, description="Brief reasoning for the decision.")
    acordao: str | None = Field(
        None, description="The full text of the decision (e.g., 'Acórdão' or 'Sentença')."
    )
    tribunal: str | None = Field(
        None, description="The court that issued the decision (e.g., 'TJRO')."
    )
    decision_date: date | None = Field(None, description="The date of the decision.")

class BatchDecisionAnalysis(BaseModel):
    results: list[DecisionAnalysis] = Field(..., description="List of analysis results, one for each provided document, in the same order.")