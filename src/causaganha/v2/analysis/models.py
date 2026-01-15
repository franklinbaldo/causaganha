"""Pydantic models for decision analysis."""

from pydantic import BaseModel, Field


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

    decision_type: str = Field(
        description=(
            "Type of decision: 'sentença' (first instance judgment), "
            "'acórdão' (appellate decision), or 'decisão interlocutória' "
            "(interlocutory decision)"
        ),
    )
    outcome: str = Field(
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
