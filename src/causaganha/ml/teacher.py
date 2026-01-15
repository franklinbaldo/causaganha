import structlog
from pydantic_ai import Agent
from pydantic import BaseModel, Field
from causaganha.ml.types import WinnerLabel

logger = structlog.get_logger()

class TeacherResult(BaseModel):
    winner: WinnerLabel = Field(..., description="Who won the case: plaintiff_won, defendant_won, or unclear.")

class LLMTeacher:
    def __init__(self, model: str = "google-gla:gemini-2.5-flash"):
        self.agent = Agent(
            model=model,
            output_type=TeacherResult,
            system_prompt=(
                "You are a legal expert. Given the decision text, identify who won. "
                "Output exactly one of {plaintiff_won, defendant_won, unclear}. "
                "If the decision is partial or ambiguous, use unclear."
            ),
        )

    async def label(self, text: str) -> WinnerLabel:
        try:
            # Truncate text to fit context if excessively long, though Gemini handles large context well.
            # 30k chars is approx 7-10k tokens, safe for Gemini Flash (1M tokens context)
            truncated_text = text[:100000]

            result = await self.agent.run(f"Who won this case?\n\n{truncated_text}")
            return result.data.winner
        except Exception as e:
            logger.warning("teacher_failed", error=str(e))
            return WinnerLabel.UNCLEAR
