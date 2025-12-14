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
    judge_name: str | None = Field(None, description="The name of the judge who signed the decision.")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0.")
