"""Decision analyzer using Pydantic AI."""

import asyncio

import structlog
from pydantic_ai import Agent

from causaganha.analysis.models import DecisionAnalysis


logger = structlog.get_logger()


class DecisionAnalyzer:
    """Analyze judicial decisions using Pydantic AI.

    Uses Google Gemini to read PDFs natively and extract
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

            return result.data

        except Exception as e:
            logger.error(
                "analysis_failed",
                intimation_id=intimation_id,
                error=str(e),
            )
            raise

    async def analyze_pdf(
        self,
        pdf_url: str,
        intimation_id: int | None = None,
    ) -> DecisionAnalysis:
        """Analyze a single PDF decision document.

        DEPRECATED: Use analyze_text() instead with texto field.
        This method is kept for backward compatibility with existing code.

        Args:
            pdf_url: URL to the PDF document.
            intimation_id: Optional intimation ID for logging.

        Returns:
            DecisionAnalysis with extracted information.

        Raises:
            Exception: If analysis fails.
        """
        logger.warning(
            "analyze_pdf_deprecated",
            message="analyze_pdf() is deprecated, use analyze_text() with texto field",
            intimation_id=intimation_id,
        )

        logger.info(
            "analyzing_pdf",
            url=pdf_url,
            intimation_id=intimation_id,
        )

        try:
            # Pydantic AI + Gemini reads PDF natively
            result = await self.agent.run(
                f"Analyze this judicial decision PDF: {pdf_url}",
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

            return result.data

        except Exception as e:
            logger.error(
                "analysis_failed",
                intimation_id=intimation_id,
                url=pdf_url,
                error=str(e),
            )
            raise

    async def analyze_batch(
        self,
        inputs: list[str],
        intimation_ids: list[int] | None = None,
        input_type: str = "text",
    ) -> list[DecisionAnalysis | Exception]:
        """Analyze multiple decisions concurrently.

        Args:
            inputs: List of decision texts or PDF URLs.
            intimation_ids: Optional list of intimation IDs (same length).
            input_type: "text" (default, recommended) or "pdf" (deprecated).

        Returns:
            List of DecisionAnalysis or Exceptions, matching the input order.
        """
        if intimation_ids is None:
            intimation_ids = [None] * len(inputs)

        logger.info(
            "batch_analysis_start",
            total=len(inputs),
            input_type=input_type,
        )

        # Create tasks based on input type
        if input_type == "text":
            tasks = [
                self.analyze_text(text, int_id)
                for text, int_id in zip(inputs, intimation_ids, strict=False)
            ]
        else:  # pdf (deprecated)
            logger.warning(
                "batch_pdf_analysis_deprecated",
                message="PDF batch analysis is deprecated, use input_type='text'",
            )
            tasks = [
                self.analyze_pdf(url, int_id)
                for url, int_id in zip(inputs, intimation_ids, strict=False)
            ]

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        successful = sum(1 for r in results if isinstance(r, DecisionAnalysis))
        failed = sum(1 for r in results if isinstance(r, Exception))

        logger.info(
            "batch_analysis_complete",
            total=len(inputs),
            successful=successful,
            failed=failed,
        )

        return list(results)
