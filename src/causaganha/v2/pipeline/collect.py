import asyncio
from datetime import date, timedelta
from typing import Any

import structlog

from causaganha.config import settings
from causaganha.v2.api.client import PJeAPIClient
from causaganha.storage.repositories.intimation import (
    store_intimations,
    store_lawyer_associations_batch,
)

logger = structlog.get_logger()

async def collect_metadata_for_court(
    tribunal: str,
    days_back: int = 1,
) -> dict[str, Any]:
    """Collect metadata from PJe API for a specific court."""
    from causaganha.storage.connection import get_connection

    con = get_connection()
    client = PJeAPIClient()

    # Calculate date range
    today = date.today()
    start_date = today - timedelta(days=days_back)

    logger.info(
        "collecting_court_range",
        tribunal=tribunal,
        start_date=start_date.isoformat(),
        end_date=today.isoformat(),
    )

    try:
        intimations = await client.get_intimations_by_court(
            sigla_tribunal=tribunal,
            data_inicio=start_date,
            data_fim=today,
        )

        if not intimations:
            logger.info("no_intimations_found", tribunal=tribunal)
            return {
                "status": "success",
                "tribunal": tribunal,
                "total_collected": 0,
                "details": [],
            }

        # Store in DuckDB
        new_count = store_intimations(con, intimations)

        # Store lawyer associations in batch
        items = [(i.id, i.destinatarioadvogados) for i in intimations]
        lawyers_stored = store_lawyer_associations_batch(con, items)

        logger.info(
            "collection_complete",
            tribunal=tribunal,
            fetched=len(intimations),
            new=new_count,
            lawyers_stored=lawyers_stored,
        )

        return {
            "status": "success",
            "tribunal": tribunal,
            "total_collected": new_count,
            "lawyers_stored": lawyers_stored,
            "details": [{"count": len(intimations), "new": new_count}],
        }

    except Exception as e:
        logger.exception(
            "collection_error",
            tribunal=tribunal,
            error=str(e),
        )
        return {
            "status": "error",
            "tribunal": tribunal,
            "error": str(e),
        }
    finally:
        await client.close()

async def collect_metadata_for_all_courts(
    courts: list[str] | None = None,
    days_back: int = 1,
    max_concurrency: int = 5,
) -> None:
    """Collect for multiple courts in parallel.

    Uses a semaphore to limit concurrent requests to the API.
    """
    if not courts:
        courts = settings.COURTS

    logger.info(
        "starting_multi_court_collection",
        count=len(courts),
        days_back=days_back,
        concurrency=max_concurrency,
    )

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _collect_with_semaphore(court: str) -> None:
        async with semaphore:
            try:
                await collect_metadata_for_court(court, days_back)
            except Exception as e:
                logger.exception("court_parallel_collection_failed", court=court, error=str(e))

    await asyncio.gather(*[_collect_with_semaphore(court) for court in courts])
