"""Analysis pipeline logic."""
import asyncio
from datetime import UTC, datetime

import structlog

from causaganha.infrastructure.ai.analyzer import DecisionAnalyzer
from causaganha.domain.factories import AnalysisResultFactory
from causaganha.domain.interfaces import AnalysisRepositoryProtocol, IntimationRepositoryProtocol
from causaganha.domain.models import Intimation
from causaganha.infrastructure.clients.document import DocumentService
from causaganha.ml.types import WinnerClassifierMode, WinnerBootstrapMode
from causaganha.ml.runner import WinnerClassifierRunner

logger = structlog.get_logger()


async def run_analysis(
    repository: IntimationRepositoryProtocol,
    analysis_repository: AnalysisRepositoryProtocol,
    doc_service: DocumentService,
    analyzer: DecisionAnalyzer,
    limit: int = 10,
    batch_size: int = 5,
    winner_classifier_mode: WinnerClassifierMode = WinnerClassifierMode.OFF,
    jobs: int = 4,
    winner_bootstrap_mode: WinnerBootstrapMode = WinnerBootstrapMode.AUTO,
    winner_bootstrap_limit: int = 5000,
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
        winner_classifier_mode: Mode for winner prediction subsystem.
        jobs: Concurrency level for winner classifier.
        winner_bootstrap_mode: Bootstrap mode.
        winner_bootstrap_limit: Bootstrap limit.
    """
    logger.info("starting_analysis", limit=limit)

    # Initialize winner classifier runner
    # Note: We cast analysis_repository because the Protocol doesn't include the raw connection needed by bootstrapper
    # ideally we should improve the interface or pass the concrete repo.
    # Assuming runtime passed the concrete repo.
    winner_runner = WinnerClassifierRunner(
        mode=winner_classifier_mode,
        bootstrap_mode=winner_bootstrap_mode,
        bootstrap_limit=winner_bootstrap_limit,
        jobs=jobs,
        analysis_repo=analysis_repository, # type: ignore
    )

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

            # Winner Classifier hook
            ml_result = {}
            if winner_classifier_mode != WinnerClassifierMode.OFF:
                try:
                    # Construct text for embedding/teacher from analysis result
                    # Using summary + reasoning as proxy for decision text
                    text_context = f"{analysis.summary}\n\n{analysis.decision_reasoning}"
                    ml_result = await winner_runner.process_decision(text_context)
                except Exception as e:
                    logger.error("winner_classifier_failed", id=intimation_id, error=str(e))

            # Merge ML results into the final dict
            result = AnalysisResultFactory.create_result(item, analysis=analysis)
            if ml_result:
                result.update(ml_result)
            return result

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
