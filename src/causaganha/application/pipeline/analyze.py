"""Analysis pipeline logic."""
import asyncio
from datetime import UTC, datetime

import structlog

from causaganha.infrastructure.ai.analyzer import DecisionAnalyzer
from causaganha.domain.factories import AnalysisResultFactory
from causaganha.domain.interfaces import AnalysisRepositoryProtocol, IntimationRepositoryProtocol
from causaganha.domain.models import Intimation
from causaganha.infrastructure.clients.document import DocumentService
from causaganha.ml.embeddings import GeminiEmbedder
from causaganha.ml.online_learner import WinnerPredictor
from causaganha.ml.teacher import LLMTeacher, WinnerLabel
from causaganha.ml.worker_pool import WorkerPool

logger = structlog.get_logger()


async def run_analysis(
    repository: IntimationRepositoryProtocol,
    analysis_repository: AnalysisRepositoryProtocol,
    doc_service: DocumentService,
    analyzer: DecisionAnalyzer,
    limit: int = 10,
    batch_size: int = 5,
    winner_classifier_mode: str = "off",
    winner_classifier_jobs: int = 4,
) -> None:
    """Run the analysis pipeline."""
    logger.info("starting_analysis", limit=limit, winner_classifier_mode=winner_classifier_mode)

    ml_components = {}
    if winner_classifier_mode != "off":
        try:
            ml_components["embedder"] = GeminiEmbedder()
            ml_components["predictor"] = WinnerPredictor()
            if winner_classifier_mode == "teach":
                ml_components["teacher"] = LLMTeacher()
            ml_components["pool"] = WorkerPool(max_workers=winner_classifier_jobs)
        except Exception as e:
            logger.error("ml_component_initialization_failed", error=str(e))
            # Decide if we should continue without ML or stop
            return

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
            # Standard LLM analysis
            analysis = await analyzer.analyze_decision(pdf_bytes)
            logger.info("analysis_success", id=intimation_id, outcome=analysis.outcome)

            # ML Winner Classifier Logic
            if winner_classifier_mode != "off":
                pdf_text = " ".join(await doc_service.extract_text_from_pdf(pdf_bytes)) # Assuming this method exists
                embedding = await ml_components["embedder"].embed_text(pdf_text)
                pred_class, pred_conf = ml_components["predictor"].predict(embedding)

                analysis.ml_prediction = "plaintiff_won" if pred_class == 1 else "defendant_won"
                analysis.ml_confidence = pred_conf
                analysis.ml_model_version = "0.1.0" # Placeholder

                if winner_classifier_mode == "teach":
                    teacher_label = await ml_components["teacher"].get_label(pdf_text)
                    analysis.teacher_label = teacher_label.value
                    if teacher_label != WinnerLabel.UNCLEAR:
                        true_label = 1 if teacher_label == WinnerLabel.PLAINTIFF_WON else 0
                        # The update should be non-blocking
                        await ml_components["pool"].run_in_parallel([(ml_components["predictor"].update, [embedding, true_label])])


            return AnalysisResultFactory.create_result(item, analysis=analysis)

        except Exception as e:
            logger.exception("analysis_failed", id=intimation_id, error=str(e))
            return AnalysisResultFactory.create_result(item, error=str(e))

    processed = 0
    while processed < limit:
        current_limit = min(batch_size, limit - processed)
        items = await repository.get_unanalyzed_intimations(limit=current_limit)

        if not items:
            logger.info("no_more_items_to_analyze")
            break

        tasks = [process_item(item) for item in items]
        if tasks:
            results = await asyncio.gather(*tasks)
            valid_results = [r for r in results if r is not None]

            if valid_results:
                await analysis_repository.store_analysis_results_batch(valid_results)

        processed += len(items)

    if "pool" in ml_components:
        ml_components["pool"].shutdown()

    logger.info("analysis_complete", processed=processed)
