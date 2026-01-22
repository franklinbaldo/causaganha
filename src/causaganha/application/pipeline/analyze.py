"""Analysis pipeline logic."""

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
    """Run the analysis pipeline using bulk processing on decision text.

    1. Fetch unanalyzed intimations.
    2. Collect text content from intimations.
    3. Analyze with AI in bulk.
    4. Store results.

    Args:
        repository: Storage repository.
        doc_service: Document service (unused now, kept for interface compatibility).
        analyzer: Decision analyzer service.
        limit: Total items to process.
        batch_size: Items per batch.
    """
    logger.info("starting_analysis", limit=limit, batch_size=batch_size)

    processed = 0
    while processed < limit:
        # Fetch a batch
        current_limit = min(batch_size, limit - processed)
        items = await repository.get_unanalyzed_intimations(limit=current_limit)

        if not items:
            logger.info("no_more_items_to_analyze")
            break

        logger.info("processing_batch", size=len(items))

        items_ready_for_analysis: list[tuple[Intimation, str]] = []
        results_to_store = []

        # 1. Filter valid content
        for item in items:
            if item.texto and item.texto.strip():
                items_ready_for_analysis.append((item, item.texto))
            else:
                logger.warning("skipping_analysis_no_text", id=item.id)
                results_to_store.append(
                    AnalysisResultFactory.create_result(
                        item,
                        error="No text content available",
                    ),
                )

        # 2. Bulk Analyze
        if items_ready_for_analysis:
            texts_to_analyze = [text for _, text in items_ready_for_analysis]
            try:
                analyses = await analyzer.analyze_bulk(texts_to_analyze)

                # Check for mismatch
                if len(analyses) != len(items_ready_for_analysis):
                    logger.error(
                        "analysis_count_mismatch",
                        sent=len(items_ready_for_analysis),
                        received=len(analyses),
                    )
                    # Fallback: Mark all as error to be safe
                    for item, _ in items_ready_for_analysis:
                        results_to_store.append(
                            AnalysisResultFactory.create_result(
                                item,
                                error="Bulk analysis mismatch",
                            ),
                        )
                else:
                    # Map results
                    for i, analysis in enumerate(analyses):
                        item, _ = items_ready_for_analysis[i]
                        logger.info("analysis_success", id=item.id, outcome=analysis.outcome)
                        results_to_store.append(
                            AnalysisResultFactory.create_result(item, analysis=analysis),
                        )

            except Exception as e:
                logger.exception("bulk_analysis_failed", error=str(e))
                # Mark all in this batch as failed
                for item, _ in items_ready_for_analysis:
                    results_to_store.append(
                        AnalysisResultFactory.create_result(
                            item,
                            error=f"Bulk analysis exception: {e!s}",
                        ),
                    )

        # 3. Store Results
        if results_to_store:
            await analysis_repository.store_analysis_results_batch(results_to_store)

        processed += len(items)

    logger.info("analysis_complete", processed=processed)
