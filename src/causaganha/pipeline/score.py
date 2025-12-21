"""Scoring pipeline."""

import structlog

from causaganha.scoring.openskill import create_rating, get_openskill_model, rate_teams
from causaganha.storage.repository import IntimationRepository


logger = structlog.get_logger()


async def run_scoring(repository: IntimationRepository, limit: int = 100) -> None:
    """Run the scoring pipeline.

    Args:
        repository: Storage repository.
        limit: Max number of cases to process.
    """
    logger.info("starting_scoring")

    # Get unscored analyses
    unscored = await repository.get_unscored_analyses(limit=limit)

    if not unscored:
        logger.info("no_unscored_cases")
        return

    logger.info("processing_scoring_batch", count=len(unscored))

    model = get_openskill_model()

    # Collect all needed lawyers
    needed_lawyers = set()
    for row in unscored:
        if row.get("winner_lawyer_oab") and row.get("winner_lawyer_state"):
            needed_lawyers.add((row["winner_lawyer_oab"], row["winner_lawyer_state"]))
        if row.get("loser_lawyer_oab") and row.get("loser_lawyer_state"):
            needed_lawyers.add((row["loser_lawyer_oab"], row["loser_lawyer_state"]))

    # Fetch existing ratings
    existing_ratings_data = await repository.get_lawyer_ratings(list(needed_lawyers))

    # Map (oab, state) -> Rating object
    ratings_cache = {}

    # Initialize cache from DB results
    for r in existing_ratings_data:
        key = (r["oab_number"], r["oab_state"])
        rating = create_rating(model, mu=r["mu"], sigma=r["sigma"], name=f"{key[0]}-{key[1]}")
        rating.stats = {
            "total_cases": r["total_cases"],
            "wins": r["wins"],
            "losses": r["losses"],
        }
        ratings_cache[key] = rating

    # Ensure all needed lawyers are in cache (create new if missing)
    for oab, state in needed_lawyers:
        if (oab, state) not in ratings_cache:
            rating = create_rating(model, name=f"{oab}-{state}")
            rating.stats = {"total_cases": 0, "wins": 0, "losses": 0}
            ratings_cache[(oab, state)] = rating

    processed_ids = []

    for row in unscored:
        try:
            winner_oab = row.get("winner_lawyer_oab")
            winner_state = row.get("winner_lawyer_state")
            loser_oab = row.get("loser_lawyer_oab")
            loser_state = row.get("loser_lawyer_state")

            if not (winner_oab and winner_state and loser_oab and loser_state):
                continue

            r_winner = ratings_cache.get((winner_oab, winner_state))
            r_loser = ratings_cache.get((loser_oab, loser_state))

            if not r_winner or not r_loser:
                continue

            # Determine result for OpenSkill
            result_code = "win_a"  # Winner (A) vs Loser (B)

            # Update ratings
            new_winner, new_loser = rate_teams(model, [r_winner], [r_loser], result_code)

            # Update cache objects
            r_winner_updated = new_winner[0]
            if not hasattr(r_winner, "stats"):
                r_winner.stats = {"total_cases": 0, "wins": 0, "losses": 0}

            # Copy stats and increment
            r_winner_updated.stats = r_winner.stats.copy()
            r_winner_updated.stats["total_cases"] += 1
            r_winner_updated.stats["wins"] += 1
            ratings_cache[(winner_oab, winner_state)] = r_winner_updated

            r_loser_updated = new_loser[0]
            if not hasattr(r_loser, "stats"):
                r_loser.stats = {"total_cases": 0, "wins": 0, "losses": 0}

            r_loser_updated.stats = r_loser.stats.copy()
            r_loser_updated.stats["total_cases"] += 1
            r_loser_updated.stats["losses"] += 1
            ratings_cache[(loser_oab, loser_state)] = r_loser_updated

            processed_ids.append(row["id"])

        except Exception as e:
            logger.exception("scoring_failed_for_case", id=row["id"], error=str(e))

    # Persist ratings to DB
    logger.info("persisting_ratings", count=len(ratings_cache))

    ratings_to_save = []
    for (oab, state), rating in ratings_cache.items():
        stats = getattr(rating, "stats", {"total_cases": 0, "wins": 0, "losses": 0})
        ratings_to_save.append(
            {
                "oab_number": oab,
                "oab_state": state,
                "mu": rating.mu,
                "sigma": rating.sigma,
                "total_cases": stats["total_cases"],
                "wins": stats["wins"],
                "losses": stats["losses"],
            },
        )

    if ratings_to_save:
        await repository.save_lawyer_ratings(ratings_to_save)

    # Mark analysis as scored
    if processed_ids:
        await repository.mark_analyses_scored(processed_ids)

    logger.info("scoring_complete", processed=len(processed_ids))
