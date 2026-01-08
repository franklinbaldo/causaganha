"""Decision analyzer using Pydantic AI"""

from pydantic_ai import Agent, BinaryContent
import httpx
import structlog
from typing import List, Optional
from .models import DecisionAnalysis

logger = structlog.get_logger()

class DecisionAnalyzer:
    """
    Analyze judicial decisions using Pydantic AI

    Uses Google Gemini to read PDFs natively and extract
    structured information about case outcomes
    """

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        provider: str = "google-gla"
    ):
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
        self.agent = Agent(
            f'{provider}:{model_name}',
            result_type=DecisionAnalysis,
            system_prompt=system_prompt
        )

        logger.info("analyzer_initialized",
                   model=model_name,
                   provider=provider)

    async def analyze_pdf(
        self,
        pdf_url: str,
        intimation_id: Optional[int] = None
    ) -> DecisionAnalysis:
        """
        Analyze a single PDF decision document

        Args:
            pdf_url: URL to the PDF document
            intimation_id: Optional intimation ID for logging

        Returns:
            DecisionAnalysis with extracted information

        Raises:
            Exception: If analysis fails
        """
        logger.info("analyzing_pdf",
                   url=pdf_url,
                   intimation_id=intimation_id)

        try:
            # Download PDF
            async with httpx.AsyncClient() as client:
                response = await client.get(pdf_url, follow_redirects=True)
                response.raise_for_status()
                pdf_content = response.content

            # Pydantic AI + Gemini reads PDF natively
            # Pass content as BinaryContent
            result = await self.agent.run(
                [
                    "Analyze this judicial decision PDF.",
                    BinaryContent(data=pdf_content, media_type='application/pdf')
                ],
                message_history=[]
            )

            # Log results
            logger.info("analysis_complete",
                       intimation_id=intimation_id,
                       winner_oab=result.data.winner_lawyer_oab,
                       loser_oab=result.data.loser_lawyer_oab,
                       decision_type=result.data.decision_type,
                       outcome=result.data.outcome,
                       confidence=result.data.confidence_score)

            return result.data

        except Exception as e:
            logger.error("analysis_failed",
                        intimation_id=intimation_id,
                        url=pdf_url,
                        error=str(e))
            raise

    async def analyze_batch(
        self,
        pdf_urls: List[str],
        intimation_ids: Optional[List[int]] = None
    ) -> List[DecisionAnalysis]:
        """
        Analyze multiple PDFs concurrently

        Args:
            pdf_urls: List of PDF URLs
            intimation_ids: Optional list of intimation IDs (same length)

        Returns:
            List of DecisionAnalysis results (only successful ones)
        """
        import asyncio

        if intimation_ids is None:
            intimation_ids = [None] * len(pdf_urls)

        logger.info("batch_analysis_start",
                   total=len(pdf_urls))

        # Create tasks
        tasks = [
            self.analyze_pdf(url, int_id)
            for url, int_id in zip(pdf_urls, intimation_ids)
        ]

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Separate successes from failures
        analyses = [r for r in results if isinstance(r, DecisionAnalysis)]
        errors = [r for r in results if isinstance(r, Exception)]

        logger.info("batch_analysis_complete",
                   total=len(pdf_urls),
                   successful=len(analyses),
                   failed=len(errors))

        return analyses
