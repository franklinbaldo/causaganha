"""Pydantic AI analysis."""

from . import ground_truth


__all__ = ["ground_truth"]

from typing import Any

import structlog

from causaganha.analysis.analyzer import DecisionAnalyzer
from causaganha.analysis.hybrid_analyzer import HybridAnalyzer
from causaganha.analysis.rag_analyzer import RAGAnalyzer
from causaganha.analysis.strategy import AnalysisStrategy


logger = structlog.get_logger()


async def create_analyzer(
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
