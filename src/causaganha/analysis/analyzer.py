"""Analyzer for judicial decisions."""
import structlog
from pydantic_ai import Agent, BinaryContent
from causaganha.analysis.models import DecisionAnalysis

logger = structlog.get_logger()

class DecisionAnalyzer:
    """Analyzer for judicial decisions using Pydantic AI."""

    agent: Agent

    def __init__(self, api_key: str | None = None, model: str = "google-gla:gemini-2.5-flash") -> None:
        """
        Initialize the DecisionAnalyzer.

        Args:
            api_key: Optional API key (deprecated/unused if env var set).
            model: The model name to use.
        """
        # api_key is unused but kept for interface compatibility
        self.agent = Agent(
            model=model,
            output_type=DecisionAnalysis,
            system_prompt=(
                "You are a legal expert analyzing judicial decisions from Brazil. "
                "Analyze the provided PDF document and extract the outcome, summary, and judge's name."
            ),
        )

    async def analyze_decision(self, pdf_bytes: bytes) -> DecisionAnalysis:
        """
        Analyze a PDF decision and extract structured data.

        Args:
            pdf_bytes: The PDF content as bytes.

        Returns:
            DecisionAnalysis: The extracted structured data.
        """
        logger.info("analyzing_decision", size=len(pdf_bytes))

        result = await self.agent.run(
            [
                "Analyze this PDF decision.",
                BinaryContent(data=pdf_bytes, media_type="application/pdf"),
            ]
        )
        return result.data
