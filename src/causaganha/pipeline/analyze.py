"""PDF analysis pipeline"""

from typing import Any

import structlog

from causaganha.analysis.analyzer import DecisionAnalysis, DecisionAnalyzer
from causaganha.storage.connection import get_connection
from causaganha.storage.queries import get_unanalyzed_intimations


logger = structlog.get_logger()


async def analyze_pending_decisions(
    batch_size: int = 10, max_batches: int = None,
) -> dict[str, Any]:
    """Analyze pending decision PDFs

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
        if max_batches is not None and batches_processed >= max_batches:
            logger.info("batch_limit_reached", batches=batches_processed)
            break

        # Get pending intimations
        pending = get_unanalyzed_intimations(con, limit=batch_size)

        if not pending:
            logger.info("no_pending_intimations")
            break

        logger.info("processing_batch", batch=batches_processed + 1, size=len(pending))

        # Extract URLs and IDs
        pdf_urls = [p["link"] for p in pending]
        intimation_ids = [p["id"] for p in pending]

        # Analyze batch
        try:
            results = await analyzer.analyze_batch(pdf_urls, intimation_ids)

            # Store results
            for result, intimation_id in zip(results, intimation_ids):
                if isinstance(result, Exception):
                    # Failed analysis
                    logger.warning("analysis_error", intimation_id=intimation_id, error=str(result))
                    _mark_as_analyzed(con, intimation_id, success=False, error=str(result))
                    total_failed += 1
                else:
                    # Successful analysis
                    try:
                        _store_analysis(con, intimation_id, result)
                        _mark_as_analyzed(con, intimation_id, success=True)
                        total_analyzed += 1
                    except Exception as e:
                        logger.error("store_failed", intimation_id=intimation_id, error=str(e))
                        _mark_as_analyzed(con, intimation_id, success=False, error=str(e))
                        total_failed += 1

        except Exception as e:
            logger.error("batch_failed", error=str(e))
            # Mark all as failed if batch failed catastrophically
            for intimation_id in intimation_ids:
                _mark_as_analyzed(con, intimation_id, success=False, error=str(e))
            total_failed += len(intimation_ids)

        batches_processed += 1

    logger.info(
        "analysis_complete", batches=batches_processed, analyzed=total_analyzed, failed=total_failed,
    )

    return {
        "batches_processed": batches_processed,
        "analyzed": total_analyzed,
        "failed": total_failed,
        "status": "success",
    }


def _store_analysis(con, intimation_id: int, analysis: DecisionAnalysis):
    """Store analysis results"""
    if not hasattr(con, "con"):
        raise ValueError("Backend is not DuckDB compatible")

    db_con = con.con

    db_con.execute(
        """
        INSERT INTO decision_analysis (
            intimation_id,
            winner_lawyer_oab, winner_lawyer_state, winner_party_name,
            loser_lawyer_oab, loser_lawyer_state, loser_party_name,
            decision_type, outcome, judge_name,
            decision_reasoning, confidence_score,
            model_used, model_provider
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'gemini-2.5-flash', 'google'
        )
        ON CONFLICT (intimation_id) DO UPDATE SET
            winner_lawyer_oab = EXCLUDED.winner_lawyer_oab,
            winner_lawyer_state = EXCLUDED.winner_lawyer_state,
            confidence_score = EXCLUDED.confidence_score
    """,
        [
            intimation_id,
            analysis.winner_lawyer_oab,
            analysis.winner_lawyer_state,
            analysis.winner_party_name,
            analysis.loser_lawyer_oab,
            analysis.loser_lawyer_state,
            analysis.loser_party_name,
            analysis.decision_type,
            analysis.outcome,
            analysis.judge_name,
            analysis.decision_reasoning,
            analysis.confidence_score,
        ],
    )


def _mark_as_analyzed(con, intimation_id: int, success: bool, error: str = None):
    """Mark intimation as analyzed"""
    if not hasattr(con, "con"):
        raise ValueError("Backend is not DuckDB compatible")

    db_con = con.con

    db_con.execute(
        """
        UPDATE intimations
        SET
            analyzed = ?,
            analyzed_at = CASE WHEN ? THEN now() ELSE NULL END,
            analysis_attempted_at = now(),
            analysis_error = ?
        WHERE id = ?
    """,
        [success, success, error if error else None, intimation_id],
    )
