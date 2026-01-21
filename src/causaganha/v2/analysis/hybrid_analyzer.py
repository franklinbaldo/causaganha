"""Hybrid analyzer combining RAG and LLM for optimal cost/accuracy."""

import structlog

from causaganha.v2.analysis.analyzer import DecisionAnalyzer
from causaganha.v2.analysis.models import DecisionAnalysis
from causaganha.v2.analysis.rag_analyzer import RAGAnalyzer


logger = structlog.get_logger()

# Default confidence threshold for RAG vs LLM fallback
DEFAULT_CONFIDENCE_THRESHOLD = 0.70


class HybridAnalyzer:
    """Hybrid analyzer using RAG first with LLM fallback for low confidence."""

    def __init__(
        self,
        rag_analyzer: RAGAnalyzer,
        llm_analyzer: DecisionAnalyzer,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        """Initialize hybrid analyzer.

        Args:
            rag_analyzer: RAG analyzer instance.
            llm_analyzer: LLM analyzer instance.
            confidence_threshold: Minimum confidence for RAG. Below this triggers LLM.
        """
        self.rag = rag_analyzer
        self.llm = llm_analyzer
        self.threshold = confidence_threshold

        logger.info(
            "hybrid_analyzer_initialized",
            confidence_threshold=confidence_threshold,
        )

    async def analyze_text(
        self,
        text: str,
        intimation_id: int | None = None,
        pdf_url: str | None = None,
    ) -> DecisionAnalysis:
        """Analyze decision using hybrid strategy.

        Tries RAG first. If confidence is below threshold and PDF URL is available,
        falls back to LLM analysis.

        Args:
            text: Decision text to analyze.
            intimation_id: Optional intimation ID for logging.
            pdf_url: Optional PDF URL for LLM fallback.

        Returns:
            DecisionAnalysis with best available result.
        """
        logger.info(
            "hybrid_analysis_start",
            intimation_id=intimation_id,
            has_pdf_url=pdf_url is not None,
        )

        # Step 1: Try RAG analysis (cheap)
        try:
            rag_result = await self.rag.analyze_text(text, intimation_id)

            logger.info(
                "rag_analysis_complete",
                intimation_id=intimation_id,
                confidence=rag_result.rag_confidence,
                outcome=rag_result.outcome,
            )

            # Step 2: Check if confidence is high enough
            if rag_result.rag_confidence and rag_result.rag_confidence >= self.threshold:
                # High confidence RAG result - use it
                rag_result.analysis_method = "rag"

                logger.info(
                    "hybrid_using_rag",
                    intimation_id=intimation_id,
                    confidence=rag_result.rag_confidence,
                    threshold=self.threshold,
                )

                return rag_result

            # Step 3: Low confidence - try LLM fallback if PDF available
            if pdf_url:
                logger.info(
                    "hybrid_triggering_llm_fallback",
                    intimation_id=intimation_id,
                    rag_confidence=rag_result.rag_confidence,
                    threshold=self.threshold,
                )

                try:
                    llm_result = await self.llm.analyze_pdf(pdf_url, intimation_id)

                    # Preserve RAG information in the result
                    llm_result.analysis_method = "hybrid"
                    llm_result.rag_confidence = rag_result.rag_confidence
                    llm_result.rag_votes = rag_result.rag_votes

                    logger.info(
                        "hybrid_llm_fallback_success",
                        intimation_id=intimation_id,
                        llm_confidence=llm_result.confidence_score,
                        rag_confidence=rag_result.rag_confidence,
                    )

                    return llm_result

                except Exception as e:
                    logger.error(
                        "hybrid_llm_fallback_failed",
                        intimation_id=intimation_id,
                        error=str(e),
                    )
                    # Return RAG result as fallback
                    rag_result.analysis_method = "rag_low_confidence"
                    return rag_result

            else:
                # No PDF available for LLM fallback
                logger.warning(
                    "hybrid_no_pdf_for_fallback",
                    intimation_id=intimation_id,
                    rag_confidence=rag_result.rag_confidence,
                )

                rag_result.analysis_method = "rag_low_confidence"
                return rag_result

        except Exception as e:
            logger.error(
                "hybrid_rag_analysis_failed",
                intimation_id=intimation_id,
                error=str(e),
            )

            # RAG failed - try LLM if available
            if pdf_url:
                logger.info(
                    "hybrid_using_llm_due_to_rag_failure",
                    intimation_id=intimation_id,
                )

                llm_result = await self.llm.analyze_pdf(pdf_url, intimation_id)
                llm_result.analysis_method = "hybrid"
                return llm_result
            # No fallback available
            raise

    async def analyze_batch(
        self,
        texts: list[str],
        intimation_ids: list[int] | None = None,
        pdf_urls: list[str | None] | None = None,
    ) -> tuple[list[DecisionAnalysis], dict]:
        """Analyze multiple decisions using hybrid strategy.

        Args:
            texts: List of decision texts.
            intimation_ids: Optional list of intimation IDs.
            pdf_urls: Optional list of PDF URLs for LLM fallback.

        Returns:
            Tuple of:
                - List of DecisionAnalysis results
                - Statistics dictionary with cost and method usage
        """
        if intimation_ids is None:
            intimation_ids = [None] * len(texts)
        if pdf_urls is None:
            pdf_urls = [None] * len(texts)

        logger.info("hybrid_batch_analysis_start", total=len(texts))

        results = []
        stats = {
            "total": len(texts),
            "rag_used": 0,
            "llm_used": 0,
            "rag_low_conf": 0,
            "cost_rag": 0.0,
            "cost_llm": 0.0,
        }

        for text, int_id, pdf_url in zip(
            texts,
            intimation_ids,
            pdf_urls,
            strict=False,
        ):
            try:
                result = await self.analyze_text(text, int_id, pdf_url)
                results.append(result)

                # Track statistics
                if result.analysis_method == "rag":
                    stats["rag_used"] += 1
                    stats["cost_rag"] += 0.000008
                elif result.analysis_method in ["llm", "hybrid"]:
                    stats["llm_used"] += 1
                    stats["cost_llm"] += 0.000420
                elif result.analysis_method == "rag_low_confidence":
                    stats["rag_low_conf"] += 1
                    stats["cost_rag"] += 0.000008

            except Exception as e:
                logger.error(
                    "hybrid_batch_item_failed",
                    intimation_id=int_id,
                    error=str(e),
                )
                # Add a failed result
                results.append(
                    DecisionAnalysis(
                        intimation_id=int_id or 0,
                        decision_type="ANALYSIS_FAILED",
                        outcome="UNKNOWN",
                        plaintiff_won=False,
                        confidence_score=0.0,
                        summary=f"Analysis failed: {e!s}",
                        analysis_method="failed",
                    ),
                )

        # Calculate totals
        stats["total_cost"] = stats["cost_rag"] + stats["cost_llm"]
        stats["cost_per_decision"] = stats["total_cost"] / len(texts) if texts else 0.0

        # Calculate savings compared to LLM-only
        llm_only_cost = len(texts) * 0.000420
        stats["savings_vs_llm"] = (
            (llm_only_cost - stats["total_cost"]) / llm_only_cost * 100
            if llm_only_cost > 0
            else 0.0
        )

        logger.info(
            "hybrid_batch_analysis_complete",
            **stats,
        )

        return results, stats
