"""Scoring service domain logic."""

from typing import Any

import structlog

from causaganha.domain.scoring.openskill import create_rating, get_openskill_model, rate_teams
from causaganha.infrastructure.storage.repositories.analysis import AnalysisRepository
from causaganha.infrastructure.storage.repositories.lawyer import LawyerRatingRepository


logger = structlog.get_logger()


class ScoringService:
    """Service to handle lawyer scoring logic."""

    def __init__(
        self,
        analysis_repository: AnalysisRepository,
        rating_repository: LawyerRatingRepository,
    ) -> None:
        """Initialize the service.

        Args:
            analysis_repository: Repository for analysis results.
            rating_repository: Repository for lawyer ratings.
        """
        self.analysis_repo = analysis_repository
        self.rating_repo = rating_repository
        self.model = get_openskill_model()

    async def process_pending_batch(self, limit: int = 100) -> int:
        """Process a batch of unscored analyses.

        Args:
            limit: Maximum number of cases to process.

        Returns:
            Number of processed cases.
        """
        # Get unscored analyses
        unscored = await self.analysis_repo.get_unscored_analyses(limit=limit)

        if not unscored:
            logger.info("no_unscored_cases")
            return 0

        logger.info("processing_scoring_batch", count=len(unscored))

        # Collect all needed lawyers
        needed_lawyers = set()
        for row in unscored:
            if row.get("winner_lawyer_oab") and row.get("winner_lawyer_state"):
                needed_lawyers.add((row["winner_lawyer_oab"], row["winner_lawyer_state"]))
            if row.get("loser_lawyer_oab") and row.get("loser_lawyer_state"):
                needed_lawyers.add((row["loser_lawyer_oab"], row["loser_lawyer_state"]))

        # Fetch existing ratings
        existing_ratings_data = await self.rating_repo.get_lawyer_ratings(list(needed_lawyers))

        # Map (oab, state) -> Rating object
        ratings_cache = {}

        # Initialize cache from DB results
        for r in existing_ratings_data:
            key = (r["oab_number"], r["oab_state"])
            rating = create_rating(
                self.model,
                mu=r["mu"],
                sigma=r["sigma"],
                name=f"{key[0]}-{key[1]}",
            )
            rating.stats = {
                "total_cases": r["total_cases"],
                "wins": r["wins"],
                "losses": r["losses"],
            }
            ratings_cache[key] = rating

        # Ensure all needed lawyers are in cache (create new if missing)
        for oab, state in needed_lawyers:
            if (oab, state) not in ratings_cache:
                rating = create_rating(self.model, name=f"{oab}-{state}")
                rating.stats = {"total_cases": 0, "wins": 0, "losses": 0}
                ratings_cache[(oab, state)] = rating

        processed_ids = []

        for row in unscored:
            try:
                processed = self._process_single_case(row, ratings_cache)
                if processed:
                    processed_ids.append(row["id"])
            except Exception as e:
                logger.exception("scoring_failed_for_case", id=row["id"], error=str(e))

        # Persist ratings to DB
        logger.info("persisting_ratings", count=len(ratings_cache))

        ratings_to_save = []
        for (oab, state), rating in ratings_cache.items():
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
            await self.rating_repo.save_lawyer_ratings(ratings_to_save)

        # Mark analysis as scored
        if processed_ids:
            await self.analysis_repo.mark_analyses_scored(processed_ids)

        return len(processed_ids)

    def _process_single_case(self, row: dict, ratings_cache: dict) -> bool:
        """Process a single case and update ratings in cache.

        Args:
            row: Analysis result row.
            ratings_cache: Cache of ratings.

        Returns:
            True if processed successfully, False otherwise.
        """
        winner_oab = row.get("winner_lawyer_oab")
        winner_state = row.get("winner_lawyer_state")
        loser_oab = row.get("loser_lawyer_oab")
        loser_state = row.get("loser_lawyer_state")

        if not (winner_oab and winner_state and loser_oab and loser_state):
            return False

        r_winner = ratings_cache.get((winner_oab, winner_state))
        r_loser = ratings_cache.get((loser_oab, loser_state))

        if not r_winner or not r_loser:
            return False

        # Determine result for OpenSkill
        result_code = "win_a"  # Winner (A) vs Loser (B)

        # Update ratings
        new_winner, new_loser = rate_teams(
            self.model, [r_winner], [r_loser], result_code,
        )

        # Update cache objects
        self._update_rating_stats(ratings_cache, (winner_oab, winner_state), new_winner[0], is_win=True)
        self._update_rating_stats(ratings_cache, (loser_oab, loser_state), new_loser[0], is_win=False)

        return True

    def _update_rating_stats(
        self,
        cache: dict,
        key: tuple[str, str],
        new_rating: Any,
        is_win: bool,
    ) -> None:
        """Update rating and statistics in cache."""
        current_rating = cache[key]

        if not hasattr(current_rating, "stats"):
            current_rating.stats = {"total_cases": 0, "wins": 0, "losses": 0}

        # Copy stats and increment
        new_rating.stats = current_rating.stats.copy()
        new_rating.stats["total_cases"] += 1
        if is_win:
            new_rating.stats["wins"] += 1
        else:
            new_rating.stats["losses"] += 1

        cache[key] = new_rating
