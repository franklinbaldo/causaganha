"""Analyzer for judicial decisions."""
import asyncio
from typing import Iterable

import structlog
from pydantic_ai import Agent, BinaryContent

from causaganha.domain.models_analysis import BatchDecisionAnalysis, DecisionAnalysis


logger = structlog.get_logger()


class DecisionAnalyzer:
    """Analyzer for judicial decisions using Pydantic AI."""

    agent: Agent
    batch_agent: Agent

    def __init__(self, api_key: str | None = None, model: str = "google-gla:gemini-2.5-flash") -> None:
        """Initialize the DecisionAnalyzer.

        Args:
            api_key: Optional API key (deprecated/unused if env var set).
            model: The model name to use.
        """
        # Single decision agent
        self.agent = Agent(
            model=model,
            output_type=DecisionAnalysis,
            system_prompt=(
                "You are a legal expert analyzing judicial decisions from Brazil. "
                "Analyze the provided decision text or PDF and extract structured information about the case outcome. "
                "Identify the winning and losing parties and their lawyers (OAB number and state). "
                "Determine the decision type and outcome. Provide a brief summary and the judge's name."
            ),
        )

        # Batch decision agent
        self.batch_agent = Agent(
            model=model,
            output_type=BatchDecisionAnalysis,
            system_prompt=(
                "You are a legal expert analyzing judicial decisions from Brazil. "
                "You will receive multiple decision texts. "
                "For EACH decision, analyze it and extract structured information about the case outcome. "
                "Return a list of analysis results. "
                "CRITICAL: The results MUST correspond exactly to the order of the provided texts. "
                "The first result must be for the first text, the second result for the second text, and so on."
            ),
        )

    async def analyze_decision(self, content: str | bytes) -> DecisionAnalysis:
        """Analyze a decision and extract structured data."""
        logger.info("analyzing_decision", length=len(content))

        if isinstance(content, bytes):
            payload = [
                "Analyze this PDF decision.",
                BinaryContent(data=content, media_type="application/pdf"),
            ]
        else:
            payload = f"Analyze this decision:\n\n{content}"

        result = await self.agent.run(payload)
        return result.data

    async def analyze_bulk(self, texts: Iterable[str]) -> list[DecisionAnalysis]:
        """Analyze multiple decision texts in a single API call."""
        texts_list = list(texts)
        if not texts_list:
            return []

        logger.info("analyzing_bulk_decisions", count=len(texts_list))

        user_content = ["Analyze the following decisions in order."]
        for i, text in enumerate(texts_list):
            user_content.append(f"--- DECISION {i + 1} START ---")
            user_content.append(text)
            user_content.append(f"--- DECISION {i + 1} END ---")

        result = await self.batch_agent.run(user_content)

        if len(result.data.results) != len(texts_list):
            logger.warning(
                "batch_analysis_count_mismatch",
                expected=len(texts_list),
                got=len(result.data.results),
            )

        return result.data.results

    async def analyze_batch_concurrent(self, texts: list[str]) -> list[DecisionAnalysis | Exception]:
        """Analyze multiple decisions concurrently (individual calls)."""

        logger.info("starting_concurrent_analysis", count=len(texts))

        tasks = [self.analyze_decision(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return list(results)
