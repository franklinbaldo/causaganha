"""PDF analysis pipeline."""

from typing import Any

import structlog

from causaganha.v2.analysis.analyzer import DecisionAnalyzer
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
) -> dict[str, Any]:
    """Analyze pending decision PDFs.

    Args:
        batch_size: Number of PDFs to process at once
        max_batches: Maximum number of batches to process (None = all)

    Returns:
        Dictionary with statistics
    """
    logger.info("analysis_start", batch_size=batch_size, max_batches=max_batches)

    con = get_connection()
    analyzer = DecisionAnalyzer()

    total_analyzed = 0
    total_failed = 0
    batches_processed = 0

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

        # Extract URLs and IDs
        pdf_urls = [p["link"] for p in pending]
        intimation_ids = [p["id"] for p in pending]

        # Analyze batch
        try:
            analyses = await analyzer.analyze_batch(pdf_urls, intimation_ids)

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

    logger.info(
        "analysis_complete",
        batches=batches_processed,
        analyzed=total_analyzed,
        failed=total_failed,
    )

    return {
        "batches_processed": batches_processed,
        "analyzed": total_analyzed,
        "failed": total_failed,
        "status": "success",
    }
