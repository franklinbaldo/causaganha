"""Analysis pipeline logic."""
import structlog
import httpx
from datetime import datetime, timezone
from causaganha.storage.connection import get_connection
from causaganha.storage.schema import create_schema
from causaganha.storage.queries import get_unanalyzed_intimations, store_analysis_result
from causaganha.analysis.analyzer import DecisionAnalyzer

logger = structlog.get_logger()

async def download_pdf(url: str) -> bytes | None:
    """Download PDF from URL.

    Args:
        url: The URL to download from.

    Returns:
        The content bytes or None if failed.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Using client.request to avoid type checking issues with dynamic get method
            resp = await client.request("GET", url, follow_redirects=True, timeout=30.0)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "application/pdf" not in content_type and not url.lower().endswith(".pdf"):
                logger.warning("url_not_pdf", url=url, content_type=content_type)
            return resp.content
        except Exception:
            logger.exception("download_failed", url=url)
            return None

async def run_analysis(db_path: str, limit: int = 10, batch_size: int = 5) -> None:
    """Run the analysis pipeline.

    1. Fetch unanalyzed intimations.
    2. Download PDF.
    3. Analyze with AI.
    4. Store results.

    Args:
        db_path: Path to DuckDB file.
        limit: Total items to process.
        batch_size: Items per batch.
    """
    logger.info("starting_analysis", db_path=db_path, limit=limit)

    con = get_connection(db_path)
    create_schema(con)

    analyzer = DecisionAnalyzer()

    processed = 0
    while processed < limit:
        # Fetch a batch
        current_limit = min(batch_size, limit - processed)
        items = await get_unanalyzed_intimations(con, limit=current_limit)

        if not items:
            logger.info("no_more_items_to_analyze")
            break

        for item in items:
            intimation_id = item["id"]
            link = item["link"]

            logger.info("processing_intimation", id=intimation_id, link=link)

            if not link:
                logger.warning("missing_link", id=intimation_id)
                continue

            pdf_bytes = await download_pdf(link)
            if not pdf_bytes:
                await store_analysis_result(con, {
                    "id": int(datetime.now(timezone.utc).timestamp() * 1000),
                    "intimation_id": intimation_id,
                    "outcome": "UNKNOWN",
                    "summary": "Download failed",
                    "judge_name": None,
                    "confidence_score": 0.0,
                    "analyzed_at": datetime.now(timezone.utc)
                })
                continue

            try:
                analysis = await analyzer.analyze_decision(pdf_bytes)

                await store_analysis_result(con, {
                    "id": int(datetime.now(timezone.utc).timestamp() * 1000),
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
                })
                logger.info("analysis_success", id=intimation_id, outcome=analysis.outcome)

            except Exception as e:
                logger.exception("analysis_failed", id=intimation_id, error=str(e))
                await store_analysis_result(con, {
                    "id": int(datetime.now(timezone.utc).timestamp() * 1000),
                    "intimation_id": intimation_id,
                    "outcome": "UNKNOWN",
                    "summary": f"Analysis failed: {str(e)}",
                    "judge_name": None,
                    "confidence_score": 0.0,
                    "analyzed_at": datetime.now(timezone.utc)
                })

            processed += 1

    logger.info("analysis_complete", processed=processed)
