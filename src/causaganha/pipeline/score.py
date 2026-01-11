"""Scoring pipeline."""

import structlog

from causaganha.domain.interfaces import AnalysisRepositoryProtocol, LawyerRatingRepositoryProtocol
from causaganha.domain.services.scoring import ScoringService


logger = structlog.get_logger()


async def run_scoring(
    analysis_repository: AnalysisRepositoryProtocol,
    rating_repository: LawyerRatingRepositoryProtocol,
    limit: int = 100,
) -> None:
    """Run the scoring pipeline.

    Args:
        analysis_repository: Analysis repository.
        rating_repository: Lawyer rating repository.
        limit: Max number of cases to process.
    """
    logger.info("starting_scoring")

    service = ScoringService(analysis_repository, rating_repository)
    processed = await service.process_pending_batch(limit=limit)

    logger.info("scoring_complete", processed=processed)
