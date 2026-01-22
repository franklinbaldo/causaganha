"""Rating calculation pipeline."""

from typing import Any

import structlog

from causaganha.domain.scoring.openskill import (
    create_rating,
    get_openskill_model,
    rate_teams,
)
from causaganha.storage.connection import get_connection
from causaganha.storage.queries import (
    get_lawyer_name,
    get_lawyer_rating,
    get_unrated_analyses,
    mark_analysis_as_rated,
    update_lawyer_rating,
)


logger = structlog.get_logger()


async def calculate_ratings(
    batch_size: int = 100,
) -> dict[str, Any]:
    """Calculate ratings for unrated analyses.

    Args:
        batch_size: Number of analyses to process.

    Returns:
        Dictionary with statistics.
    """
    logger.info("rating_calculation_start", batch_size=batch_size)

    con = get_connection()
    model = get_openskill_model()

    processed = 0
    failed = 0

    try:
        # Get unrated analyses
        analyses = get_unrated_analyses(con, limit=batch_size)

        if not analyses:
            logger.info("no_unrated_analyses")
            return {
                "processed": 0,
                "failed": 0,
                "status": "success",
            }

        for analysis in analyses:
            try:
                # Get participants
                winner_oab = analysis["winner_lawyer_oab"]
                winner_state = analysis["winner_lawyer_state"]

                loser_oab = analysis["loser_lawyer_oab"]
                loser_state = analysis["loser_lawyer_state"]

                # Get current ratings
                winner_data = get_lawyer_rating(con, winner_oab, winner_state)
                loser_data = get_lawyer_rating(con, loser_oab, loser_state)

                # Resolve names
                winner_name = winner_data.get("lawyer_name") if winner_data else None
                if not winner_name:
                    winner_name = get_lawyer_name(con, winner_oab, winner_state)

                loser_name = loser_data.get("lawyer_name") if loser_data else None
                if not loser_name:
                    loser_name = get_lawyer_name(con, loser_oab, loser_state)

                # Create rating objects
                if winner_data:
                    winner_rating = create_rating(
                        model, mu=winner_data["mu"], sigma=winner_data["sigma"]
                    )
                    winner_wins = winner_data["wins"]
                    winner_losses = winner_data["losses"]
                else:
                    winner_rating = create_rating(model)
                    winner_wins = 0
                    winner_losses = 0

                if loser_data:
                    loser_rating = create_rating(
                        model, mu=loser_data["mu"], sigma=loser_data["sigma"]
                    )
                    loser_wins = loser_data["wins"]
                    loser_losses = loser_data["losses"]
                else:
                    loser_rating = create_rating(model)
                    loser_wins = 0
                    loser_losses = 0

                # Calculate new ratings (Win for A)
                # outcome "procedente" -> Winner won (Team A)
                new_winner, new_loser = rate_teams(
                    model,
                    [winner_rating],
                    [loser_rating],
                    result="win_a",
                )

                # Update ratings in DB
                # Winner
                update_lawyer_rating(
                    con,
                    oab_number=winner_oab,
                    oab_state=winner_state,
                    lawyer_name=winner_name,
                    mu=new_winner[0].mu,
                    sigma=new_winner[0].sigma,
                    wins=winner_wins + 1,
                    losses=winner_losses,
                )

                # Loser
                update_lawyer_rating(
                    con,
                    oab_number=loser_oab,
                    oab_state=loser_state,
                    lawyer_name=loser_name,
                    mu=new_loser[0].mu,
                    sigma=new_loser[0].sigma,
                    wins=loser_wins,
                    losses=loser_losses + 1,
                )

                # Mark as rated
                mark_analysis_as_rated(con, analysis["id"])
                processed += 1

            except Exception as e:
                logger.error("rating_failed", analysis_id=analysis["id"], error=str(e))
                failed += 1

        logger.info(
            "rating_calculation_complete",
            processed=processed,
            failed=failed,
        )

        return {
            "processed": processed,
            "failed": failed,
            "status": "success",
        }

    except Exception as e:
        logger.error("rating_pipeline_failed", error=str(e))
        return {
            "processed": processed,
            "failed": failed,
            "status": "failed",
            "error": str(e),
        }
