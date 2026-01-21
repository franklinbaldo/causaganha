"""Metadata collection pipeline."""

import asyncio
from datetime import date, timedelta
from typing import Any

import structlog

from causaganha.v2.api.client import PJeAPIClient
from causaganha.v2.storage.connection import get_connection
from causaganha.v2.storage.migrations import run_migrations
from causaganha.v2.storage.queries import store_intimations, store_lawyer_associations


logger = structlog.get_logger()

# Flag to track if migrations have been run this session
_migrations_run = False


def ensure_migrations() -> None:
    """Run database migrations if not already done this session."""
    global _migrations_run
    if not _migrations_run:
        try:
            con = get_connection()
            run_migrations(con)
            _migrations_run = True
        except Exception as e:
            logger.warning("migrations_check_failed", error=str(e))


async def collect_metadata_for_court(
    sigla_tribunal: str,
    days_back: int = 7,
    max_items: int | None = None,
) -> dict[str, Any]:
    """Collect intimation metadata from PJe API for a court.

    Args:
        sigla_tribunal: Court code (e.g., 'TJRO', 'TJMT')
        days_back: How many days back to fetch
        max_items: Maximum items to fetch (None = all available)

    Returns:
        Dictionary with statistics
    """
    # Ensure database schema is up to date
    ensure_migrations()

    logger.info(
        "collection_start",
        tribunal=sigla_tribunal,
        days_back=days_back,
        max_items=max_items,
    )

    client = PJeAPIClient()
    con = get_connection()

    try:
        # Calculate date range
        today = date.today()
        start_date = today - timedelta(days=days_back)

        logger.info(
            "fetching_from_api",
            tribunal=sigla_tribunal,
            start_date=start_date.isoformat(),
            end_date=today.isoformat(),
        )

        # Fetch from API with rate limit handling
        intimations = await client.get_intimations_by_court(
            sigla_tribunal=sigla_tribunal,
            data_inicio=start_date,
            data_fim=today,
            max_items=max_items,
        )

        if not intimations:
            logger.warning(
                "no_intimations_fetched",
                tribunal=sigla_tribunal,
                start_date=start_date.isoformat(),
                end_date=today.isoformat(),
            )
            return {
                "tribunal": sigla_tribunal,
                "intimations_fetched": 0,
                "intimations_new": 0,
                "lawyers_stored": 0,
                "status": "success",
                "note": "No data available for date range",
            }

        logger.info(
            "api_fetch_complete",
            tribunal=sigla_tribunal,
            count=len(intimations),
        )

        # Store intimations
        new_count = store_intimations(con, intimations)

        # Store lawyer associations
        lawyers_stored = 0
        for intimation in intimations:
            count = store_lawyer_associations(
                con,
                intimation.id,
                intimation.destinatarioadvogados,
            )
            lawyers_stored += count

        logger.info(
            "collection_complete",
            tribunal=sigla_tribunal,
            intimations_fetched=len(intimations),
            intimations_new=new_count,
            lawyers_stored=lawyers_stored,
        )

        return {
            "tribunal": sigla_tribunal,
            "intimations_fetched": len(intimations),
            "intimations_new": new_count,
            "lawyers_stored": lawyers_stored,
            "status": "success",
        }

    except Exception as e:
        logger.exception(
            "collection_failed",
            tribunal=sigla_tribunal,
            error=str(e),
        )
        return {
            "tribunal": sigla_tribunal,
            "status": "failed",
            "error": str(e),
        }

    finally:
        await client.close()


async def collect_metadata_for_all_courts(
    courts: list[str],
    days_back: int = 7,
) -> list[dict[str, Any]]:
    """Collect metadata for multiple courts concurrently.

    Args:
        courts: List of court codes
        days_back: How many days back to fetch

    Returns:
        List of result dictionaries
    """
    logger.info("multi_court_collection_start", courts=courts, count=len(courts))

    tasks = [collect_metadata_for_court(court, days_back) for court in courts]

    results = await asyncio.gather(*tasks)

    successful = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")

    logger.info(
        "multi_court_collection_complete",
        total=len(courts),
        successful=successful,
        failed=failed,
    )

    return list(results)
