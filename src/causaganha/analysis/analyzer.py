"""Decision analyzer using Pydantic AI."""

import asyncio

import structlog
from pydantic_ai import Agent

from causaganha.analysis.models import DecisionAnalysis


logger = structlog.get_logger()


class DecisionAnalyzer:
    """Analyze judicial decisions using Pydantic AI.

    Uses Google Gemini to analyze decision text and extract
    structured information about case outcomes.
    """

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        provider: str = "google-gla",
    ) -> None:
        """Initialize the analyzer."""
        self.model_name = model_name
        self.provider = provider

        # System prompt for the AI
        system_prompt = """
        You are an expert Brazilian legal analyst specializing in judicial decisions.

        Your task is to read judicial decision documents and extract structured
        information about case outcomes for a lawyer performance rating system.

        CRITICAL REQUIREMENTS:
        1. Identify the winning and losing parties with precision
        2. Extract the correct OAB numbers for each lawyer
        3. Determine the decision type and outcome accurately
        4. Provide a brief summary of the judge's reasoning
        5. Use confidence_score to indicate uncertainty:
           - 0.9-1.0: Very confident, all information clear
           - 0.7-0.9: Confident, minor ambiguities
           - 0.5-0.7: Moderate confidence, some unclear elements
           - <0.5: Low confidence, significant ambiguities

        IMPORTANT NOTES:
        - OAB numbers are usually in format: "OAB/XX NNNNN" (e.g., "OAB/RO 5733")
        - In Brazilian law:
           * "Autor" or "Requerente" = plaintiff/claimant
           * "Réu" or "Requerido" = defendant/respondent
           * "Procedente" means the plaintiff won
           * "Improcedente" means the defendant won
           * "Parcialmente procedente" = partial victory (treat as plaintiff win)
        - Decision types:
           * "Sentença" = first instance judgment
           * "Acórdão" = appellate court decision
           * "Decisão interlocutória" = interlocutory decision

        If critical information is missing or unclear, reflect this in your
        confidence_score. Never guess OAB numbers - if unclear, indicate in
        confidence_score.
        """

        # Create Pydantic AI agent
        # Updated for pydantic-ai >= 1.0 (uses output_type instead of result_type)
        self.agent = Agent(
            f"{provider}:{model_name}",
            output_type=DecisionAnalysis,
            system_prompt=system_prompt,
        )

        logger.info(
            "analyzer_initialized",
            model=model_name,
            provider=provider,
        )

    async def analyze_text(
        self,
        decision_text: str,
        intimation_id: int | None = None,
    ) -> DecisionAnalysis:
        """Analyze a decision from text content.

        Args:
            decision_text: Full text of the judicial decision.
            intimation_id: Optional intimation ID for logging.

        Returns:
            DecisionAnalysis with extracted information.

        Raises:
            Exception: If analysis fails.
        """
        logger.info(
            "analyzing_text",
            text_length=len(decision_text),
            intimation_id=intimation_id,
        )

        try:
            # Use Gemini to analyze text directly (no PDF needed!)
            result = await self.agent.run(
                f"Analyze this judicial decision:\n\n{decision_text}",
                message_history=[],
            )

            # Log results
            logger.info(
                "analysis_complete",
                intimation_id=intimation_id,
                winner_oab=result.data.winner_lawyer_oab,
                loser_oab=result.data.loser_lawyer_oab,
                decision_type=result.data.decision_type,
                outcome=result.data.outcome,
                confidence=result.data.confidence_score,
            )
        except Exception as e:
            logger.exception(
                "analysis_failed",
                intimation_id=intimation_id,
                error=str(e),
            )
            raise
        else:
            return result.data

    async def analyze_batch(
        self,
        texts: list[str],
        intimation_ids: list[int] | None = None,
    ) -> list[DecisionAnalysis | Exception]:
        """Analyze multiple decisions concurrently.

        Args:
            texts: List of decision texts.
            intimation_ids: Optional list of intimation IDs (same length).

        Returns:
            List of DecisionAnalysis or Exceptions, matching the input order.
        """
        if intimation_ids is None:
            intimation_ids = [None] * len(texts)

        logger.info(
            "batch_analysis_start",
            total=len(texts),
        )

        # Create tasks for text analysis
        tasks = [
            self.analyze_text(text, int_id)
            for text, int_id in zip(texts, intimation_ids, strict=False)
        ]

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        successful = sum(1 for r in results if isinstance(r, DecisionAnalysis))
        failed = sum(1 for r in results if isinstance(r, Exception))

        logger.info(
            "batch_analysis_complete",
            total=len(texts),
            successful=successful,
            failed=failed,
        )

        return list(results)
