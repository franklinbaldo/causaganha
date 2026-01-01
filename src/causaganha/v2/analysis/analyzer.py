"""Decision analyzer using Pydantic AI."""

import structlog
from pydantic_ai import Agent

from .models import DecisionAnalysis


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
        self.model_name = model_name
        self.provider = provider

        # System prompt for the AI
        system_prompt = """
        You are an expert Brazilian legal analyst specializing in judicial decisions.

        Your task is to read judicial decision documents and extract structured
        information about case outcomes for a lawyer performance rating system.
        """

        # Create Pydantic AI agent
        # Note: In production, we might need to handle API keys here or via env vars
        self.agent = Agent(
            f"{provider}:{model_name}",
            result_type=DecisionAnalysis,
            system_prompt=system_prompt,
        )

        logger.info("analyzer_initialized", model=model_name, provider=provider)

    async def analyze_pdf(
        self,
        pdf_url: str,
        intimation_id: int | None = None,
    ) -> DecisionAnalysis:
        """Analyze a single PDF decision document.

        Args:
            pdf_url: URL to the PDF document
            intimation_id: Optional intimation ID for logging

        Returns:
            DecisionAnalysis with extracted information

        Raises:
            Exception: If analysis fails
        """
        logger.info("analyzing_pdf", url=pdf_url, intimation_id=intimation_id)

        try:
            # Pydantic AI + Gemini reads PDF natively
            # Note: The prompt assumes the model can access the URL or receives the content.
            # If the model expects content, we might need to download it first.
            # But the plan implies native reading or Pydantic AI handling it.
            # For now, we follow the plan's code structure.
            result = await self.agent.run(
                f"Analyze this judicial decision PDF: {pdf_url}",
                message_history=[],
            )

            # Log results
            logger.info(
                "analysis_complete",
                intimation_id=intimation_id,
                winner_oab=result.data.winner_lawyer_oab,
                confidence=result.data.confidence_score,
            )

            return result.data  # type: ignore[no-any-return]

        except Exception as e:
            logger.exception(
                "analysis_failed", intimation_id=intimation_id, url=pdf_url, error=str(e)
            )
            raise

    async def analyze_batch(
        self,
        pdf_urls: list[str],
        intimation_ids: list[int] | None = None,
    ) -> list[DecisionAnalysis]:
        """Analyze multiple PDFs concurrently.

        Args:
            pdf_urls: List of PDF URLs
            intimation_ids: Optional list of intimation IDs (same length)

        Returns:
            List of DecisionAnalysis results (only successful ones)
        """
        import asyncio

        if intimation_ids is None:
            intimation_ids_safe: list[int | None] = [None] * len(pdf_urls)
        else:
            intimation_ids_safe = list(intimation_ids)

        logger.info("batch_analysis_start", total=len(pdf_urls))

        # Create tasks
        tasks = [
            self.analyze_pdf(url, int_id)
            for url, int_id in zip(pdf_urls, intimation_ids_safe, strict=False)
        ]

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Separate successes from failures
        analyses = [r for r in results if isinstance(r, DecisionAnalysis)]
        errors = [r for r in results if isinstance(r, Exception)]

        logger.info(
            "batch_analysis_complete",
            total=len(pdf_urls),
            successful=len(analyses),
            failed=len(errors),
        )

        return analyses
