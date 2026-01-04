"""Scoring pipeline."""

import structlog

from causaganha.domain.scoring import calculate_batch_ratings
from causaganha.storage.repository import IntimationRepository
from causaganha.storage.repositories.lawyer import LawyerRatingRepository


logger = structlog.get_logger()


async def run_scoring(
    repository: IntimationRepository,
    lawyer_repo: LawyerRatingRepository,
    limit: int = 100
) -> None:
    """Run the scoring pipeline.

    Args:
        repository: Intimation repository (for analysis results).
        lawyer_repo: Lawyer rating repository.
        limit: Max number of cases to process.
    """
    logger.info("starting_scoring")

    # Get unscored analyses
    unscored = await repository.get_unscored_analyses(limit=limit)

    if not unscored:
        logger.info("no_unscored_cases")
        return

    logger.info("processing_scoring_batch", count=len(unscored))

    # Collect all needed lawyers
    needed_lawyers = set()
    for row in unscored:
        if row.get("winner_lawyer_oab") and row.get("winner_lawyer_state"):
            needed_lawyers.add((row["winner_lawyer_oab"], row["winner_lawyer_state"]))
        if row.get("loser_lawyer_oab") and row.get("loser_lawyer_state"):
            needed_lawyers.add((row["loser_lawyer_oab"], row["loser_lawyer_state"]))

    # Fetch existing ratings using new repository
    existing_ratings_data = await lawyer_repo.get_lawyer_ratings(list(needed_lawyers))

    # Calculate new ratings using pure domain logic
    try:
        updated_ratings_map = calculate_batch_ratings(unscored, existing_ratings_data)
    except Exception as e:
        logger.exception("scoring_calculation_failed", error=str(e))
        return

    # Persist ratings to DB using new repository
    logger.info("persisting_ratings", count=len(updated_ratings_map))

    ratings_to_save = []
    for (oab, state), rating in updated_ratings_map.items():
        stats = getattr(rating, "stats", {"total_cases": 0, "wins": 0, "losses": 0})
        ratings_to_save.append({
            "oab_number": oab,
            "oab_state": state,
            "mu": rating.mu,
            "sigma": rating.sigma,
            "total_cases": stats["total_cases"],
            "wins": stats["wins"],
            "losses": stats["losses"],
        })

    if ratings_to_save:
        await lawyer_repo.save_lawyer_ratings(ratings_to_save)

    # Mark analysis as scored (this stays in IntimationRepository as it relates to AnalysisResults)
    # We mark all rows that were passed to the calculation as processed
    # Ideally calculate_batch_ratings would return processed IDs too, but strict domain separation suggests
    # we just mark the inputs as processed if no exception was raised.
    # However, to be safe, we should collect IDs from unscored list that were valid (had winner/loser info)
    processed_ids = []
    for row in unscored:
         if (row.get("winner_lawyer_oab") and row.get("winner_lawyer_state") and
             row.get("loser_lawyer_oab") and row.get("loser_lawyer_state")):
             processed_ids.append(row["id"])

    if processed_ids:
        await repository.mark_analyses_scored(processed_ids)

    logger.info("scoring_complete", processed=len(processed_ids))
