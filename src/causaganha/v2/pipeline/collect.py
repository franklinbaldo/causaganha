"""Metadata collection pipeline"""

import asyncio
import structlog
from datetime import date, timedelta
from typing import List

from ..api.client import PJeAPIClient
from ..storage.connection import get_connection
from ..storage.queries import store_intimations, store_lawyer_associations

logger = structlog.get_logger()

async def collect_metadata_for_court(
    sigla_tribunal: str,
    days_back: int = 7
) -> dict:
    """
    Collect intimation metadata from PJe API for a court

    Args:
        sigla_tribunal: Court code (e.g., 'TJRO', 'TJMT')
        days_back: How many days back to fetch

    Returns:
        Dictionary with statistics
    """
    logger.info("collection_start",
               tribunal=sigla_tribunal,
               days_back=days_back)

    client = PJeAPIClient()
    con = get_connection()

    try:
        # Calculate date range
        data_inicio = date.today() - timedelta(days=days_back)

        # Fetch from API
        intimations = await client.get_intimations_by_court(
            sigla_tribunal=sigla_tribunal,
            data_inicio=data_inicio
        )

        # Store intimations
        new_count = store_intimations(con, intimations)

        # Store lawyer associations
        lawyers_stored = 0
        for intimation in intimations:
            count = store_lawyer_associations(
                con,
                intimation.id,
                intimation.destinatarioadvogados
            )
            lawyers_stored += count

        logger.info("collection_complete",
                   tribunal=sigla_tribunal,
                   intimations_fetched=len(intimations),
                   intimations_new=new_count,
                   lawyers_stored=lawyers_stored)

        return {
            'tribunal': sigla_tribunal,
            'intimations_fetched': len(intimations),
            'intimations_new': new_count,
            'lawyers_stored': lawyers_stored,
            'status': 'success'
        }

    except Exception as e:
        logger.error("collection_failed",
                    tribunal=sigla_tribunal,
                    error=str(e))
        return {
            'tribunal': sigla_tribunal,
            'status': 'failed',
            'error': str(e)
        }

    finally:
        await client.close()

async def collect_metadata_for_all_courts(
    courts: List[str],
    days_back: int = 7
) -> List[dict]:
    """
    Collect metadata for multiple courts concurrently

    Args:
        courts: List of court codes
        days_back: How many days back to fetch

    Returns:
        List of result dictionaries
    """
    logger.info("multi_court_collection_start",
               courts=courts,
               count=len(courts))

    tasks = [
        collect_metadata_for_court(court, days_back)
        for court in courts
    ]

    results = await asyncio.gather(*tasks)

    successful = sum(1 for r in results if r['status'] == 'success')
    failed = sum(1 for r in results if r['status'] == 'failed')

    logger.info("multi_court_collection_complete",
               total=len(courts),
               successful=successful,
               failed=failed)

    return results

# CLI entry point
async def main():
    """CLI entry point for metadata collection"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m causaganha.v2.pipeline.collect TJRO [TJMT ...]")
        sys.exit(1)

    courts = sys.argv[1:]
    results = await collect_metadata_for_all_courts(courts)

    print("\nResults:")
    for result in results:
        print(f"  {result['tribunal']}: {result['status']}")
        if result['status'] == 'success':
            print(f"    Fetched: {result['intimations_fetched']}")
            print(f"    New: {result['intimations_new']}")

if __name__ == "__main__":
    asyncio.run(main())
