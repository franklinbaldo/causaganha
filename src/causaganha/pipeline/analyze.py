"""Analysis pipeline logic."""
import asyncio
import structlog
from datetime import datetime, timezone
from causaganha.analysis.analyzer import DecisionAnalyzer
from causaganha.services.document import DocumentService
from causaganha.storage.repository import IntimationRepository

logger = structlog.get_logger()


async def run_analysis(
    repository: IntimationRepository,
    doc_service: DocumentService,
    analyzer: DecisionAnalyzer,
    limit: int = 10,
    batch_size: int = 5
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

    async def process_item(item: dict) -> dict | None:
        intimation_id = item["id"]
        link = item["link"]

        logger.info("processing_intimation", id=intimation_id, link=link)

        if not link:
            logger.warning("missing_link", id=intimation_id)
            return None

        pdf_bytes = await doc_service.download_pdf(link)
        if not pdf_bytes:
            return {
                "id": int(datetime.now(timezone.utc).timestamp() * 1000) + intimation_id,  # Ensure unique ID
                "intimation_id": intimation_id,
                "outcome": "UNKNOWN",
                "summary": "Download failed",
                "judge_name": None,
                "confidence_score": 0.0,
                "analyzed_at": datetime.now(timezone.utc),
                "winner_lawyer_oab": None,
                "winner_lawyer_state": None,
                "winner_party_name": None,
                "loser_lawyer_oab": None,
                "loser_lawyer_state": None,
                "loser_party_name": None,
                "decision_type": None,
                "decision_reasoning": None,
            }

        try:
            analysis = await analyzer.analyze_decision(pdf_bytes)
            logger.info("analysis_success", id=intimation_id, outcome=analysis.outcome)

            return {
                "id": int(datetime.now(timezone.utc).timestamp() * 1000) + intimation_id,
                "intimation_id": intimation_id,
                "outcome": analysis.outcome.value,
                "summary": analysis.summary,
                "judge_name": analysis.judge_name,
                "confidence_score": analysis.confidence_score,
                "analyzed_at": datetime.now(timezone.utc),
                "winner_lawyer_oab": analysis.winner_lawyer_oab,
                "winner_lawyer_state": analysis.winner_lawyer_state,
                "winner_party_name": analysis.winner_party_name,
                "loser_lawyer_oab": analysis.loser_lawyer_oab,
                "loser_lawyer_state": analysis.loser_lawyer_state,
                "loser_party_name": analysis.loser_party_name,
                "decision_type": analysis.decision_type,
                "decision_reasoning": analysis.decision_reasoning,
            }

        except Exception as e:
            logger.exception("analysis_failed", id=intimation_id, error=str(e))
            return {
                "id": int(datetime.now(timezone.utc).timestamp() * 1000) + intimation_id,
                "intimation_id": intimation_id,
                "outcome": "UNKNOWN",
                "summary": f"Analysis failed: {str(e)}",
                "judge_name": None,
                "confidence_score": 0.0,
                "analyzed_at": datetime.now(timezone.utc),
                "winner_lawyer_oab": None,
                "winner_lawyer_state": None,
                "winner_party_name": None,
                "loser_lawyer_oab": None,
                "loser_lawyer_state": None,
                "loser_party_name": None,
                "decision_type": None,
                "decision_reasoning": None,
            }

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
                await repository.store_analysis_results_batch(valid_results)

        processed += len(items)

    logger.info("analysis_complete", processed=processed)
