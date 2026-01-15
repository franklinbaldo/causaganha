"""Module for the LLM-based teacher."""

import structlog
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from enum import Enum

logger = structlog.get_logger()

class WinnerLabel(str, Enum):
    """Enumeration for the winning side."""
    PLAINTIFF_WON = "plaintiff_won"
    DEFENDANT_WON = "defendant_won"
    UNCLEAR = "unclear"

class TeacherAnalysis(BaseModel):
    """Pydantic model for the teacher's output."""
    winner: WinnerLabel = Field(..., description="The identified winning party.")

class LLMTeacher:
    """
    An LLM-based teacher that analyzes a judicial decision text
    to determine the winning side.
    """

    def __init__(self, model: str = "google-gla:gemini-2.5-flash"):
        self.agent = Agent(
            model=model,
            output_type=TeacherAnalysis,
            system_prompt=(
                "You are a legal expert specialized in Brazilian law. Your task is to analyze "
                "the provided judicial decision text and determine which party won the dispute. "
                "Focus on identifying the plaintiff (autor) and the defendant (réu). "
                "Your output must be one of three options: "
                "1. 'plaintiff_won' if the plaintiff's primary claim was successful. "
                "2. 'defendant_won' if the defendant successfully defended against the claim. "
                "3. 'unclear' if the outcome is ambiguous, a partial win, or cannot be determined from the text."
            ),
        )

    async def get_label(self, decision_text: str) -> WinnerLabel:
        """
        Analyzes the decision text and returns a winner label.

        Args:
            decision_text: The full text of the judicial decision.

        Returns:
            The determined WinnerLabel.
        """
        logger.info("llm_teacher_analyzing_decision", text_length=len(decision_text))
        try:
            result = await self.agent.run(
                f"Analyze the following judicial decision and determine the winner:\n\n{decision_text}"
            )
            logger.info("llm_teacher_analysis_complete", winner=result.data.winner)
            return result.data.winner
        except Exception as e:
            logger.error("llm_teacher_analysis_failed", error=str(e))
            # In case of failure, return 'unclear' to avoid breaking the pipeline
            return WinnerLabel.UNCLEAR
