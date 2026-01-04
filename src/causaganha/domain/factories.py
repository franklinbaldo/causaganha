"""Factories for creating domain entities and value objects."""

from datetime import UTC, datetime

from causaganha.analysis.models import DecisionAnalysis


def create_analysis_result(
    intimation_id: int,
    analysis: DecisionAnalysis | None = None,
    error: str | None = None,
) -> dict:
    """Create a dictionary representing an analysis result.

    This encapsulates the logic for mapping LLM output (DecisionAnalysis)
    to the persistence format (dictionary matching schema), including
    handling failures and generating unique IDs.

    Args:
        intimation_id: The ID of the intimation being analyzed.
        analysis: The structured analysis result from the LLM, if successful.
        error: Error message string, if analysis failed.

    Returns:
        A dictionary matching the ANALYSIS_RESULTS_SCHEMA.
    """
    # Generate a unique ID based on timestamp and intimation ID to avoid collisions
    # (Note: In a real DB with sequences, this might be handled by the DB,
    # but for DuckDB/Ibis insert logic here, we generate it)
    result_id = int(datetime.now(UTC).timestamp() * 1000) + intimation_id

    base_result = {
        "id": result_id,
        "intimation_id": intimation_id,
        "analyzed_at": datetime.now(UTC),
    }

    if error:
        return {
            **base_result,
            "outcome": "UNKNOWN",
            "summary": f"Analysis failed: {error}",
            "judge_name": None,
            "confidence_score": 0.0,
            "winner_lawyer_oab": None,
            "winner_lawyer_state": None,
            "winner_party_name": None,
            "loser_lawyer_oab": None,
            "loser_lawyer_state": None,
            "loser_party_name": None,
            "decision_type": None,
            "decision_reasoning": None,
        }

    if analysis:
        return {
            **base_result,
            "outcome": analysis.outcome.value,
            "summary": analysis.summary,
            "judge_name": analysis.judge_name,
            "confidence_score": analysis.confidence_score,
            "winner_lawyer_oab": analysis.winner_lawyer_oab,
            "winner_lawyer_state": analysis.winner_lawyer_state,
            "winner_party_name": analysis.winner_party_name,
            "loser_lawyer_oab": analysis.loser_lawyer_oab,
            "loser_lawyer_state": analysis.loser_lawyer_state,
            "loser_party_name": analysis.loser_party_name,
            "decision_type": analysis.decision_type,
            "decision_reasoning": analysis.decision_reasoning,
        }

    # Fallback for unexpected case where neither analysis nor error is provided
    return {
        **base_result,
        "outcome": "UNKNOWN",
        "summary": "No analysis result provided",
        "judge_name": None,
        "confidence_score": 0.0,
        "winner_lawyer_oab": None,
        "winner_lawyer_state": None,
        "winner_party_name": None,
        "loser_lawyer_oab": None,
        "loser_lawyer_state": None,
        "loser_party_name": None,
        "decision_type": None,
        "decision_reasoning": None,
    }
