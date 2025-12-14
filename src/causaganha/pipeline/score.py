"""Scoring pipeline."""

import asyncio
import structlog
from typing import Any

import ibis
from causaganha.storage.connection import get_connection
from causaganha.storage.schema import create_schema
from causaganha.scoring.openskill import get_openskill_model, create_rating, rate_teams

logger = structlog.get_logger()

async def run_scoring(db_path: str, limit: int = 100) -> None:
    """Run the scoring pipeline.

    Args:
        db_path: Path to database.
        limit: Max number of cases to process.
    """
    logger.info("starting_scoring", db_path=db_path)

    con = get_connection(db_path)
    create_schema(con)

    # Run async to avoid blocking
    await asyncio.to_thread(_sync_run_scoring, con, limit)

def _sync_run_scoring(con: ibis.BaseBackend, limit: int) -> None:
    t_analysis = con.table("analysis_results")

    # Access underlying DuckDB connection for parameterized queries
    raw_con = con.con

    # Filter for unscored analyses
    # We check if 'scored' column exists and filter, or assume False/Null
    unscored = t_analysis.filter(
        (t_analysis.scored.isnull()) | (t_analysis.scored == False)
    ).filter(
        t_analysis.winner_lawyer_oab.notnull() & t_analysis.loser_lawyer_oab.notnull()
    ).limit(limit).execute()

    if unscored.empty:
        logger.info("no_unscored_cases")
        return

    logger.info("processing_scoring_batch", count=len(unscored))

    model = get_openskill_model()

    # Cache ratings in memory for this batch processing
    # Map (oab, state) -> Rating object
    ratings_cache = {}

    # Helper to get rating from DB or cache
    def get_rating(oab: str, state: str) -> Any:
        key = (oab, state)
        if key in ratings_cache:
            return ratings_cache[key]

        # Fetch from DB
        t_ratings = con.table("lawyer_ratings")
        rows = t_ratings.filter(
            (t_ratings.oab_number == oab) & (t_ratings.oab_state == state)
        ).execute()

        if not rows.empty:
            row = rows.iloc[0]
            rating = create_rating(model, mu=row['mu'], sigma=row['sigma'], name=f"{oab}-{state}")
            # Also store stats
            rating.stats = {
                'total_cases': row['total_cases'],
                'wins': row['wins'],
                'losses': row['losses']
            }
        else:
            rating = create_rating(model, name=f"{oab}-{state}")
            rating.stats = {'total_cases': 0, 'wins': 0, 'losses': 0}

        ratings_cache[key] = rating
        return rating

    count = 0
    for _, row in unscored.iterrows():
        try:
            winner_oab = row['winner_lawyer_oab']
            winner_state = row['winner_lawyer_state']
            loser_oab = row['loser_lawyer_oab']
            loser_state = row['loser_lawyer_state']
            outcome = row['outcome']

            if not (winner_oab and winner_state and loser_oab and loser_state):
                continue

            r_winner = get_rating(winner_oab, winner_state)
            r_loser = get_rating(loser_oab, loser_state)

            # Determine result for OpenSkill
            # If we identified "winner_lawyer" and "loser_lawyer", then "winner_lawyer" WON.
            result_code = 'win_a'

            # Update ratings
            new_winner, new_loser = rate_teams(model, [r_winner], [r_loser], result_code)

            # Update cache objects
            # Note: rate_teams returns NEW objects.

            # Update winner
            r_winner_updated = new_winner[0]
            # Initialize stats on new object if needed, copying from old
            if not hasattr(r_winner, 'stats'):
                 r_winner.stats = {'total_cases': 0, 'wins': 0, 'losses': 0}

            r_winner_updated.stats = r_winner.stats.copy()
            r_winner_updated.stats['total_cases'] += 1
            r_winner_updated.stats['wins'] += 1
            ratings_cache[(winner_oab, winner_state)] = r_winner_updated

            # Update loser
            if not hasattr(r_loser, 'stats'):
                 r_loser.stats = {'total_cases': 0, 'wins': 0, 'losses': 0}

            r_loser_updated = new_loser[0]
            r_loser_updated.stats = r_loser.stats.copy()
            r_loser_updated.stats['total_cases'] += 1
            r_loser_updated.stats['losses'] += 1
            ratings_cache[(loser_oab, loser_state)] = r_loser_updated

            # Mark analysis as scored
            # Use parameterized query
            raw_con.execute("UPDATE analysis_results SET scored = TRUE WHERE id = ?", [row['id']])

            count += 1

        except Exception as e:
            logger.exception("scoring_failed_for_case", id=row['id'], error=str(e))

    # Persist ratings to DB
    logger.info("persisting_ratings", count=len(ratings_cache))
    for (oab, state), rating in ratings_cache.items():
        # Upsert
        stats = getattr(rating, 'stats', {'total_cases': 0, 'wins': 0, 'losses': 0})

        try:
            raw_con.execute("""
                INSERT INTO lawyer_ratings (
                    oab_number, oab_state, lawyer_name,
                    mu, sigma, last_updated,
                    total_cases, wins, losses
                ) VALUES (
                    ?, ?, NULL,
                    ?, ?, now(),
                    ?, ?, ?
                )
                ON CONFLICT (oab_number, oab_state) DO UPDATE SET
                    mu = EXCLUDED.mu,
                    sigma = EXCLUDED.sigma,
                    last_updated = now(),
                    total_cases = EXCLUDED.total_cases,
                    wins = EXCLUDED.wins,
                    losses = EXCLUDED.losses
            """, [
                oab, state,
                rating.mu, rating.sigma,
                stats['total_cases'], stats['wins'], stats['losses']
            ])
        except Exception as e:
            logger.exception("rating_persist_failed", oab=oab, error=str(e))

    logger.info("scoring_complete", processed=count)
