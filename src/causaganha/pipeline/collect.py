"""Metadata collection pipeline."""

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from causaganha.clients.pje import PJeAPIClient
from causaganha.storage.connection import get_connection
from causaganha.storage.queries import store_intimations, store_lawyer_associations


logger = structlog.get_logger()


async def collect_metadata_for_court(
    sigla_tribunal: str,
    days_back: int = 7,
) -> dict[str, Any]:
    """Collect intimation metadata from PJe API for a court.

    Args:
        sigla_tribunal: Court code (e.g., 'TJRO', 'TJMT')
        days_back: How many days back to fetch

    Returns:
        Dictionary with statistics
    """
    logger.info(
        "collection_start",
        tribunal=sigla_tribunal,
        days_back=days_back,
    )

    client = PJeAPIClient()
    con = get_connection()

    try:
        # Calculate date range
        data_inicio = datetime.now(UTC).date() - timedelta(days=days_back)

        # Fetch from API
        intimations = await client.get_intimations_by_court(
            sigla_tribunal=sigla_tribunal,
            data_inicio=data_inicio,
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
        )
        return {
            "tribunal": sigla_tribunal,
            "status": "failed",
            # We catch generic exception to ensure pipeline continues for other courts
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
    logger.info(
        "multi_court_collection_start",
        courts=courts,
        count=len(courts),
    )

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


async def main() -> None:
    """CLI entry point for metadata collection."""
    if len(sys.argv) < 2:  # noqa: PLR2004
        print("Usage: python -m causaganha.pipeline.collect TJRO [TJMT ...]")  # noqa: T201
        sys.exit(1)

    courts = sys.argv[1:]
    results = await collect_metadata_for_all_courts(courts)

    print("\nResults:")  # noqa: T201
    for result in results:
        print(f"  {result['tribunal']}: {result['status']}")  # noqa: T201
        if result["status"] == "success":
            print(f"    Fetched: {result['intimations_fetched']}")  # noqa: T201
            print(f"    New: {result['intimations_new']}")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
