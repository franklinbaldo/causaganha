"""Factories for creating domain entities."""

from datetime import UTC, datetime

from causaganha.domain.models import Intimation
from causaganha.domain.models_analysis import DecisionAnalysis


class AnalysisResultFactory:
    """Factory for creating analysis results."""

    @staticmethod
    def _generate_id(intimation_id: int) -> int:
        """Generate a unique ID for the analysis result.

        Uses current timestamp + intimation ID to ensure uniqueness.
        """
        return int(datetime.now(UTC).timestamp() * 1000) + intimation_id

    @classmethod
    def create_result(
        cls,
        intimation: Intimation,
        analysis: DecisionAnalysis | None = None,
        error: str | None = None,
    ) -> dict[str, object]:
        """Create a dictionary representing an analysis result.

        This method encapsulates the logic for ID generation and mapping
        analysis output to the persistence schema.

        Args:
            intimation: The source intimation.
            analysis: The analysis result from the AI (optional).
            error: Error message if analysis failed (optional).

        Returns:
            A dictionary matching the analysis_results schema.
        """
        generated_id = cls._generate_id(intimation.id)

        base_result = {
            "id": generated_id,
            "intimation_id": intimation.id,
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
                "outcome": analysis.outcome.value
                if hasattr(analysis.outcome, "value")
                else analysis.outcome,
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

        # Fallback for download failure or other cases where neither analysis nor error is specific enough
        return {
            **base_result,
            "outcome": "UNKNOWN",
            "summary": "Analysis processing incomplete",
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
