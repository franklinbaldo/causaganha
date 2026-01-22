from datetime import date

import structlog

from causaganha.domain.interfaces import IntimationRepositoryProtocol
from causaganha.infrastructure.integrations.pje.client import PJeAPIClient


logger = structlog.get_logger()


async def run_collection(
    repository: IntimationRepositoryProtocol,
    client: PJeAPIClient,
    start_date: str,
    end_date: str,
    courts: list[str] | None = None,
) -> None:
    """Collects intimations from the PJe API and stores them in DuckDB.

    Args:
        repository: Intimation repository for storage.
        client: PJe API client.
        start_date: Start date for filtering (YYYY-MM-DD).
        end_date: End date for filtering (YYYY-MM-DD).
        courts: List of court acronyms to collect from. If None, defaults to configured courts.
    """
    if courts is None:
        from causaganha.config import settings

        courts = settings.COURTS

    logger.info("starting_collection", start_date=start_date, end_date=end_date, courts=courts)

    try:
        for court in courts:
            logger.info("collecting_court", court=court)
            try:
                intimations = await client.get_intimations_by_court(
                    sigla_tribunal=court,
                    data_disponibilizacao_inicio=date.fromisoformat(start_date),
                    data_disponibilizacao_fim=date.fromisoformat(end_date),
                )

                if intimations:
                    logger.info("storing_intimations", count=len(intimations), court=court)
                    await repository.store_intimations(intimations)
                else:
                    logger.info("no_intimations_found", court=court)

            except Exception as e:
                logger.exception("court_collection_failed", court=court, error=str(e))
                # Continue to next court even if one fails
                continue

    finally:
        # Note: client close is managed by the caller (Composition Root)
        pass

    logger.info("collection_complete")
