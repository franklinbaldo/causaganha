"""Analysis pipeline logic."""

import asyncio

import structlog

from causaganha.domain.factories import AnalysisResultFactory
from causaganha.domain.interfaces import AnalysisRepositoryProtocol, IntimationRepositoryProtocol
from causaganha.domain.models import Intimation
from causaganha.infrastructure.ai.analyzer import DecisionAnalyzer
from causaganha.infrastructure.clients.document import DocumentService


logger = structlog.get_logger()


async def run_analysis(
    repository: IntimationRepositoryProtocol,
    analysis_repository: AnalysisRepositoryProtocol,
    doc_service: DocumentService,
    analyzer: DecisionAnalyzer,
    limit: int = 10,
    batch_size: int = 5,
) -> None:
    """Run the analysis pipeline.

    1. Fetch unanalyzed intimations.
    2. Download PDF.
    3. Analyze with AI.
    4. Store results.

    Args:
        repository: Storage repository.
        doc_service: Document service for downloads.
        analyzer: Decision analyzer service.
        limit: Total items to process.
        batch_size: Items per batch.
    """
    logger.info("starting_analysis", limit=limit)

    async def process_item(item: Intimation) -> dict | None:
        intimation_id = item.id
        link = item.link

        logger.info("processing_intimation", id=intimation_id, link=link)

        if not link:
            logger.warning("missing_link", id=intimation_id)
            return None

        pdf_bytes = await doc_service.download_pdf(link)
        if not pdf_bytes:
            return AnalysisResultFactory.create_result(item, error="Download failed")

        try:
            analysis = await analyzer.analyze_decision(pdf_bytes)
            logger.info("analysis_success", id=intimation_id, outcome=analysis.outcome)

            return AnalysisResultFactory.create_result(item, analysis=analysis)

        except Exception as e:
            logger.exception("analysis_failed", id=intimation_id, error=str(e))
            return AnalysisResultFactory.create_result(item, error=str(e))

    processed = 0
    while processed < limit:
        # Fetch a batch
        current_limit = min(batch_size, limit - processed)
        items = await repository.get_unanalyzed_intimations(limit=current_limit)

        if not items:
            logger.info("no_more_items_to_analyze")
            break

        # Process batch concurrently
        tasks = [process_item(item) for item in items]
        if tasks:
            results = await asyncio.gather(*tasks)
            valid_results = [r for r in results if r is not None]

            # Store batch results
            if valid_results:
                await analysis_repository.store_analysis_results_batch(valid_results)

        processed += len(items)

    logger.info("analysis_complete", processed=processed)
