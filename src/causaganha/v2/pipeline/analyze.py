"""PDF analysis pipeline"""

import asyncio
import structlog
from typing import List

from ..analysis.analyzer import DecisionAnalyzer
from ..storage.connection import get_connection
from ..storage.queries import get_unanalyzed_intimations

logger = structlog.get_logger()

async def analyze_pending_decisions(
    batch_size: int = 10,
    max_batches: int = None
) -> dict:
    """
    Analyze pending decision PDFs

    Args:
        batch_size: Number of PDFs to process at once
        max_batches: Maximum number of batches to process (None = all)

    Returns:
        Dictionary with statistics
    """
    logger.info("analysis_start",
               batch_size=batch_size,
               max_batches=max_batches)

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

        logger.info("processing_batch",
                   batch=batches_processed + 1,
                   size=len(pending))

        # Extract URLs and IDs
        pdf_urls = [p['link'] for p in pending]
        intimation_ids = [p['id'] for p in pending]

        # Analyze batch
        try:
            analyses = await analyzer.analyze_batch(pdf_urls, intimation_ids)

            # Store results
            for analysis, intimation_id in zip(analyses, intimation_ids):
                try:
                    _store_analysis(con, intimation_id, analysis)
                    _mark_as_analyzed(con, intimation_id, success=True)
                    total_analyzed += 1
                except Exception as e:
                    logger.error("store_failed",
                                intimation_id=intimation_id,
                                error=str(e))
                    _mark_as_analyzed(con, intimation_id, success=False, error=str(e))
                    total_failed += 1

        except Exception as e:
            logger.error("batch_failed", error=str(e))
            # Mark all as failed
            for intimation_id in intimation_ids:
                _mark_as_analyzed(con, intimation_id, success=False, error=str(e))
            total_failed += len(intimation_ids)

        batches_processed += 1

    logger.info("analysis_complete",
               batches=batches_processed,
               analyzed=total_analyzed,
               failed=total_failed)

    return {
        'batches_processed': batches_processed,
        'analyzed': total_analyzed,
        'failed': total_failed,
        'status': 'success'
    }

def _store_analysis(con, intimation_id: int, analysis):
    """Store analysis results"""

    con.raw_sql(f"""
        INSERT INTO decision_analysis (
            intimation_id,
            winner_lawyer_oab, winner_lawyer_state, winner_party_name,
            loser_lawyer_oab, loser_lawyer_state, loser_party_name,
            decision_type, outcome, judge_name,
            decision_reasoning, confidence_score,
            model_used, model_provider
        ) VALUES (
            {intimation_id},
            '{analysis.winner_lawyer_oab}',
            '{analysis.winner_lawyer_state}',
            '{analysis.winner_party_name.replace("'", "''")}',
            '{analysis.loser_lawyer_oab}',
            '{analysis.loser_lawyer_state}',
            '{analysis.loser_party_name.replace("'", "''")}',
            '{analysis.decision_type}',
            '{analysis.outcome}',
            '{analysis.judge_name.replace("'", "''")}',
            '{analysis.decision_reasoning.replace("'", "''")}',
            {analysis.confidence_score},
            'gemini-2.5-flash',
            'google'
        )
        ON CONFLICT (intimation_id) DO UPDATE SET
            winner_lawyer_oab = EXCLUDED.winner_lawyer_oab,
            winner_lawyer_state = EXCLUDED.winner_lawyer_state,
            confidence_score = EXCLUDED.confidence_score
    """)

def _mark_as_analyzed(con, intimation_id: int, success: bool, error: str = None):
    """Mark intimation as analyzed"""

    error_val = f"'{error.replace("'", "''")}'" if error else 'NULL'
    con.raw_sql(f"""
        UPDATE intimations
        SET
            analyzed = {success},
            analyzed_at = {'CURRENT_TIMESTAMP' if success else 'NULL'},
            analysis_attempted_at = CURRENT_TIMESTAMP,
            analysis_error = {error_val}
        WHERE id = {intimation_id}
    """)

# CLI entry point
async def main():
    """CLI entry point for PDF analysis"""
    import sys

    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    max_batches = int(sys.argv[2]) if len(sys.argv) > 2 else None

    result = await analyze_pending_decisions(batch_size, max_batches)

    print(f"\nAnalysis complete:")
    print(f"  Analyzed: {result['analyzed']}")
    print(f"  Failed: {result['failed']}")
    print(f"  Batches: {result['batches_processed']}")

if __name__ == "__main__":
    asyncio.run(main())
