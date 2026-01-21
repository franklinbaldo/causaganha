"""PDF analysis pipeline with RAG and LLM support."""

from typing import Any

import structlog

from causaganha.v2.analysis.analyzer import DecisionAnalyzer
from causaganha.v2.analysis.hybrid_analyzer import HybridAnalyzer
from causaganha.v2.analysis.rag_analyzer import RAGAnalyzer
from causaganha.v2.analysis.strategy import AnalysisStrategy
from causaganha.v2.storage.connection import get_connection
from causaganha.v2.storage.queries import (
    get_unanalyzed_intimations,
    mark_as_analyzed,
    store_analysis,
)


logger = structlog.get_logger()


async def analyze_pending_decisions(
    batch_size: int = 10,
    max_batches: int | None = None,
    strategy: AnalysisStrategy | str = AnalysisStrategy.HYBRID,
    confidence_threshold: float = 0.70,
) -> dict[str, Any]:
    """Analyze pending decision PDFs using specified strategy.

    Args:
        batch_size: Number of PDFs to process at once
        max_batches: Maximum number of batches to process (None = all)
        strategy: Analysis strategy (llm, rag, hybrid, auto)
        confidence_threshold: Confidence threshold for hybrid strategy

    Returns:
        Dictionary with statistics including method usage and costs
    """
    # Convert string to enum if needed
    if isinstance(strategy, str):
        strategy = AnalysisStrategy(strategy)

    logger.info(
        "analysis_start",
        batch_size=batch_size,
        max_batches=max_batches,
        strategy=strategy.value,
        confidence_threshold=confidence_threshold,
    )

    con = get_connection()

    # Initialize analyzer(s) based on strategy
    if strategy == AnalysisStrategy.LLM:
        analyzer = DecisionAnalyzer()
        logger.info("using_llm_only_strategy")
    elif strategy == AnalysisStrategy.RAG:
        analyzer = RAGAnalyzer()
        logger.info("using_rag_only_strategy")
    else:  # HYBRID or AUTO
        rag_analyzer = RAGAnalyzer()
        llm_analyzer = DecisionAnalyzer()
        analyzer = HybridAnalyzer(rag_analyzer, llm_analyzer, confidence_threshold)
        logger.info(
            "using_hybrid_strategy",
            confidence_threshold=confidence_threshold,
        )

    total_analyzed = 0
    total_failed = 0
    batches_processed = 0

    # Track method usage for hybrid strategy
    rag_used = 0
    llm_used = 0
    total_cost = 0.0

    while True:
        # Check batch limit
        if max_batches and batches_processed >= max_batches:
            logger.info("batch_limit_reached", batches=batches_processed)
            break

        # Get pending intimations
        pending = get_unanalyzed_intimations(con, limit=batch_size)

        if not pending:
            logger.info("no_pending_intimations")
            break

        logger.info(
            "processing_batch",
            batch=batches_processed + 1,
            size=len(pending),
        )

        # Extract data based on strategy
        intimation_ids = [p["id"] for p in pending]
        pdf_urls = [p["link"] for p in pending]
        texts = [p.get("texto", "") for p in pending]

        # Analyze batch based on strategy
        try:
            if strategy == AnalysisStrategy.LLM:
                # LLM only - use PDF URLs
                analyses = await analyzer.analyze_batch(pdf_urls, intimation_ids)
            elif strategy == AnalysisStrategy.RAG:
                # RAG only - use text
                analyses = await analyzer.analyze_batch(texts, intimation_ids)
            else:  # HYBRID
                # Hybrid needs both text and PDF URLs
                results, stats = await analyzer.analyze_batch(
                    texts,
                    intimation_ids,
                    pdf_urls,
                )
                analyses = results

                # Track statistics from hybrid analyzer
                rag_used += stats.get("rag_used", 0)
                llm_used += stats.get("llm_used", 0)
                total_cost += stats.get("total_cost", 0.0)

            # Store results
            for result, intimation_id in zip(analyses, intimation_ids, strict=True):
                if isinstance(result, Exception):
                    logger.error(
                        "analysis_failed",
                        intimation_id=intimation_id,
                        error=str(result),
                    )
                    mark_as_analyzed(con, intimation_id, success=False, error=str(result))
                    total_failed += 1
                    continue

                try:
                    store_analysis(con, intimation_id, result)
                    mark_as_analyzed(con, intimation_id, success=True)
                    total_analyzed += 1
                except Exception as e:
                    logger.error(
                        "store_failed",
                        intimation_id=intimation_id,
                        error=str(e),
                    )
                    mark_as_analyzed(con, intimation_id, success=False, error=str(e))
                    total_failed += 1

        except Exception as e:
            logger.error("batch_failed", error=str(e))
            # Mark all as failed
            for intimation_id in intimation_ids:
                mark_as_analyzed(con, intimation_id, success=False, error=str(e))
            total_failed += len(intimation_ids)

        batches_processed += 1

    # Calculate cost for non-hybrid strategies
    if strategy == AnalysisStrategy.LLM:
        total_cost = total_analyzed * 0.000420
        llm_used = total_analyzed
    elif strategy == AnalysisStrategy.RAG:
        total_cost = total_analyzed * 0.000008
        rag_used = total_analyzed

    # Calculate savings vs LLM-only
    llm_only_cost = total_analyzed * 0.000420
    savings_pct = ((llm_only_cost - total_cost) / llm_only_cost * 100) if llm_only_cost > 0 else 0.0

    logger.info(
        "analysis_complete",
        batches=batches_processed,
        analyzed=total_analyzed,
        failed=total_failed,
        strategy=strategy.value,
        rag_used=rag_used,
        llm_used=llm_used,
        total_cost=f"${total_cost:.6f}",
        savings_vs_llm=f"{savings_pct:.1f}%",
    )

    return {
        "batches_processed": batches_processed,
        "analyzed": total_analyzed,
        "failed": total_failed,
        "strategy": strategy.value,
        "rag_used": rag_used,
        "llm_used": llm_used,
        "total_cost": total_cost,
        "cost_per_decision": total_cost / total_analyzed if total_analyzed > 0 else 0.0,
        "savings_vs_llm_pct": savings_pct,
        "status": "success",
    }
