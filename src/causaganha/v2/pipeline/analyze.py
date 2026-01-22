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


async def _initialize_analyzer(
    strategy: AnalysisStrategy,
    confidence_threshold: float,
) -> Any:
    """Initialize the appropriate analyzer based on strategy."""
    if strategy == AnalysisStrategy.LLM:
        logger.info("using_llm_only_strategy")
        return DecisionAnalyzer()

    if strategy == AnalysisStrategy.RAG:
        logger.info("using_rag_only_strategy")
        return await RAGAnalyzer.create()

    # HYBRID or AUTO
    logger.info(
        "using_hybrid_strategy",
        confidence_threshold=confidence_threshold,
    )
    rag_analyzer = await RAGAnalyzer.create()
    llm_analyzer = DecisionAnalyzer()
    return HybridAnalyzer(rag_analyzer, llm_analyzer, confidence_threshold)


async def _process_batch_results(
    con: Any,
    analyses: list[Any],
    intimation_ids: list[int],
    stats: dict[str, Any] | None = None,
) -> tuple[int, int]:
    """Process and store batch analysis results."""
    total_analyzed = 0
    total_failed = 0

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
            logger.exception(
                "store_failed",
                intimation_id=intimation_id,
                error=str(e),
            )
            mark_as_analyzed(con, intimation_id, success=False, error=str(e))
            total_failed += 1

    return total_analyzed, total_failed


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
    analyzer = await _initialize_analyzer(strategy, confidence_threshold)

    total_analyzed = 0
    total_failed = 0
    batches_processed = 0

    # Track usage statistics
    usage_stats = {
        "rag_used": 0,
        "llm_used": 0,
        "total_cost": 0.0,
    }

    while True:
        if max_batches and batches_processed >= max_batches:
            logger.info("batch_limit_reached", batches=batches_processed)
            break

        pending = get_unanalyzed_intimations(con, limit=batch_size)
        if not pending:
            logger.info("no_pending_intimations")
            break

        logger.info("processing_batch", batch=batches_processed + 1, size=len(pending))

        intimation_ids = [p["id"] for p in pending]
        pdf_urls = [p["link"] for p in pending]
        texts = [p.get("texto", "") for p in pending]

        try:
            analyses = []

            if strategy == AnalysisStrategy.LLM:
                analyses = await analyzer.analyze_batch(pdf_urls, intimation_ids)
                usage_stats["llm_used"] += len(analyses)
                usage_stats["total_cost"] += len(analyses) * 0.000420

            elif strategy == AnalysisStrategy.RAG:
                analyses = await analyzer.analyze_batch(texts, intimation_ids)
                usage_stats["rag_used"] += len(analyses)
                usage_stats["total_cost"] += len(analyses) * 0.000008

            else:  # HYBRID
                analyses, batch_stats = await analyzer.analyze_batch(
                    texts,
                    intimation_ids,
                    pdf_urls,
                )
                usage_stats["rag_used"] += batch_stats.get("rag_used", 0)
                usage_stats["llm_used"] += batch_stats.get("llm_used", 0)
                usage_stats["total_cost"] += batch_stats.get("total_cost", 0.0)

            analyzed, failed = await _process_batch_results(
                con,
                analyses,
                intimation_ids,
            )
            total_analyzed += analyzed
            total_failed += failed

        except Exception as e:
            logger.exception("batch_failed", error=str(e))
            for intimation_id in intimation_ids:
                mark_as_analyzed(con, intimation_id, success=False, error=str(e))
            total_failed += len(intimation_ids)

        batches_processed += 1

    # Calculate savings
    llm_only_cost = total_analyzed * 0.000420
    savings_pct = (
        ((llm_only_cost - usage_stats["total_cost"]) / llm_only_cost * 100)
        if llm_only_cost > 0
        else 0.0
    )

    logger.info(
        "analysis_complete",
        batches=batches_processed,
        analyzed=total_analyzed,
        failed=total_failed,
        strategy=strategy.value,
        **usage_stats,
        savings_vs_llm=f"{savings_pct:.1f}%",
    )

    return {
        "batches_processed": batches_processed,
        "analyzed": total_analyzed,
        "failed": total_failed,
        "strategy": strategy.value,
        **usage_stats,
        "cost_per_decision": (
            usage_stats["total_cost"] / total_analyzed if total_analyzed > 0 else 0.0
        ),
        "savings_vs_llm_pct": savings_pct,
        "status": "success",
    }
