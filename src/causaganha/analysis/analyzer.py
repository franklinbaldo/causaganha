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
        You are an expert Brazilian legal analyst. Your job is to extract structured
        data from DJEN (Diário de Justiça Eletrônico Nacional) judicial communications
        to power a lawyer performance rating system (similar to an Elo/OpenSkill rating).

        ── DECISION TYPE ────────────────────────────────────────────────────────────
        Classify the decision as one of:
        • "sentença"              - first-instance merit judgment (juiz singular)
        • "acórdão"               - appellate panel decision (turma/câmara)
        • "decisão interlocutória" - procedural/interim order, NOT a final ruling

        For "decisão interlocutória" there is no winner or loser yet. Set
        outcome="unknown", plaintiff_won=False, confidence_score≤0.4, and leave
        winner/loser fields null.

        ── OUTCOME ──────────────────────────────────────────────────────────────────
        Map the dispositivo (operative part) to ONE of:
        • "procedente"            - claim granted in full -> plaintiff wins
        • "parcialmente procedente" - claim partially granted -> plaintiff wins
          (even partial victories count as wins for rating purposes)
        • "improcedente"          - claim denied -> defendant wins
        • "acordo"                - parties settled, judge homologated ("homologação de acordo", "transação") -> draw
        • "extinto sem mérito"    - dismissed without prejudice (Art. 485 CPC) -> nobody wins
        • "unknown"               - cannot determine from the text

        Set plaintiff_won=True for "procedente" or "parcialmente procedente",
        False otherwise. Keep outcome and plaintiff_won CONSISTENT.

        ── ACÓRDÃOS (APPEALS) ────────────────────────────────────────────────────
        The outcome must reflect the FINAL result after the appeal, not the
        first-instance outcome being reviewed. Look for "dá provimento",
        "nega provimento", "reforma a sentença" in the dispositivo.

        ── LAWYER / OAB EXTRACTION ──────────────────────────────────────────────
        OAB numbers appear as: "OAB/RO 5733", "OAB-SP 123456", "OAB nº 5733/RO".
        Rules:
        1. Extract ONLY digits for winner_lawyer_oab / loser_lawyer_oab.
        2. Extract the two-letter state abbreviation for winner_lawyer_state /
           loser_lawyer_state (e.g. "RO", "SP").
        3. If a party has multiple lawyers, prefer the first-listed (lead counsel).
        4. If a party is unrepresented (without counsel) or represented by a
           public defender (Defensoria Pública), set the OAB field to null, NOT
           to a made-up number.
        5. NEVER invent OAB numbers. If the number is illegible or absent, set
           the field to null and lower confidence_score accordingly.

        ── CONFIDENCE SCORE ─────────────────────────────────────────────────────
        0.9-1.0 All required fields clearly present in the text
        0.7-0.9 Minor ambiguity (e.g. party names unclear, but OAB numbers found)
        0.5-0.7 Significant ambiguity (e.g. multiple possible outcomes, or OAB
                numbers missing for one side)
        0.3-0.5 Critical fields missing or contradictory signals in the text
        <0.3    Cannot reliably extract winner/loser (use this for
                "decisão interlocutória" or purely procedural notices)

        ── WHAT TO EXTRACT ──────────────────────────────────────────────────────
        • winner_party_name / loser_party_name: exact name as it appears in the text
        • judge_name: signing judge (sentença) or rapporteur (acórdão)
        • decision_reasoning: 1-2 sentences summarising the legal basis (not the
          procedural history)
        • summary: one sentence describing what the case is about
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
                "Extract structured data from the judicial communication below.\n\n"
                "Focus on:\n"
                "1. The dispositivo (operative part) to determine outcome\n"
                "2. OAB numbers for the winning and losing lawyers\n"
                "3. Whether this is a final merit decision or a procedural order\n\n"
                f"DOCUMENT:\n{decision_text}",
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
