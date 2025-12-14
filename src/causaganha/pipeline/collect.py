from datetime import date

import structlog

from causaganha.api.client import PJeAPIClient
from causaganha.storage.connection import get_connection
from causaganha.storage.queries import store_intimations
from causaganha.storage.schema import create_schema


logger = structlog.get_logger()

async def run_collection(db_path: str, start_date: str, end_date: str, courts: list[str] | None = None) -> None:
    """Collects intimations from the PJe API and stores them in DuckDB.

    Args:
        db_path: Path to the DuckDB database file.
        start_date: Start date for filtering (YYYY-MM-DD).
        end_date: End date for filtering (YYYY-MM-DD).
        courts: List of court acronyms to collect from (e.g. ['TJRO', 'TJMT']). Defaults to ['TJRO'].
    """
    if courts is None:
        courts = ["TJRO"]

    logger.info("starting_collection", db_path=db_path, start_date=start_date, end_date=end_date, courts=courts)

    # Initialize Storage
    con = get_connection(db_path)
    create_schema(con)

    # Initialize API Client
    client = PJeAPIClient()
    try:
        for court in courts:
            logger.info("collecting_court", court=court)
            try:
                intimations = await client.get_intimations_by_court(
                    sigla_tribunal=court,
                    data_inicio=date.fromisoformat(start_date),
                    data_fim=date.fromisoformat(end_date),
                )

                if intimations:
                    logger.info("storing_intimations", count=len(intimations), court=court)
                    await store_intimations(con, intimations)
                else:
                    logger.info("no_intimations_found", court=court)

            except Exception as e:
                logger.exception("court_collection_failed", court=court, error=str(e))
                # Continue to next court even if one fails
                continue

    finally:
        await client.close()

    logger.info("collection_complete")
