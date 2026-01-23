import structlog
from datetime import date, timedelta
from typing import List, Dict, Any

from causaganha.api.client import PJeAPIClient
from causaganha.storage.connection import get_connection
from causaganha.storage.queries import store_intimations

logger = structlog.get_logger()


async def collect_metadata_for_court(court: str, days_back: int) -> Dict[str, Any]:
    """Collect intimations for a specific court from PJe API."""
    today = date.today()
    start_date = today - timedelta(days=days_back)

    logger.info(
        "collecting_metadata",
        court=court,
        days_back=days_back,
        start_date=start_date.isoformat(),
    )

    client = PJeAPIClient()
    try:
        intimations = await client.get_intimations_by_court(
            court,
            data_inicio=start_date,
            data_fim=today,
        )
    finally:
        await client.close()

    con = get_connection()

    # Use the storage layer to handle persistence
    inserted_count = store_intimations(con, intimations)

    logger.info(
        "collection_complete",
        court=court,
        fetched=len(intimations),
        inserted=inserted_count,
    )

    return {
        "status": "success",
        "intimations_new": inserted_count,
        "court": court,
        "fetched": len(intimations),
    }


async def collect_metadata_for_all_courts(
    courts: List[str], days_back: int
) -> Dict[str, Any]:
    """Collect metadata for multiple courts."""
    results = {}
    for court in courts:
        try:
            res = await collect_metadata_for_court(court, days_back)
            results[court] = res
        except Exception as e:
            logger.error("collect_court_failed", court=court, error=str(e))
            results[court] = {"status": "error", "error": str(e)}
    return results
