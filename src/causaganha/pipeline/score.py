"""Rating calculation pipeline."""

from typing import Any

import structlog

from causaganha.scoring.openskill import (
    create_rating,
    get_openskill_model,
    rate_teams,
)
from causaganha.storage.connection import get_connection
from causaganha.storage.repositories.analysis import (
    get_unrated_analyses,
    mark_analysis_as_rated,
)
from causaganha.storage.repositories.intimation import get_lawyer_name
from causaganha.storage.repositories.rating import (
    LawyerRatingUpdate,
    RatingSnapshot,
    get_lawyer_rating,
    insert_rating_snapshot,
    update_lawyer_rating,
)


logger = structlog.get_logger()


# Confidence thresholds that gate how the OpenSkill rating is updated.
# - below CONFIDENCE_FLOOR: skip entirely (don't trust the classifier).
# - CONFIDENCE_FLOOR <= c < CONFIDENCE_FULL: interpolate towards the new rating
#   with weight ``c``, so low-confidence matches nudge ratings less.
# - at or above CONFIDENCE_FULL: apply the full OpenSkill delta.
CONFIDENCE_FLOOR = 0.6
CONFIDENCE_FULL = 0.8


def _interpolate_rating(
    old_rating: Any,
    new_rating: Any,
    weight: float,
    model: Any,
) -> Any:
    """Blend an updated rating with the prior based on classifier confidence.

    Weight of 1.0 returns ``new_rating`` unchanged; weight of 0.0 returns the
    prior. Values in between produce a rating whose mu/sigma are the linear
    blend of the two endpoints, which is the simplest honest way to propagate
    classifier uncertainty without forking the OpenSkill library.
    """
    w = max(0.0, min(1.0, float(weight)))
    mu = old_rating.mu + w * (new_rating.mu - old_rating.mu)
    sigma = old_rating.sigma + w * (new_rating.sigma - old_rating.sigma)
    return create_rating(model, mu=mu, sigma=sigma)


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
    skipped_low_confidence = 0
    skipped_missing_oab = 0

    try:
        # Get unrated analyses
        analyses = get_unrated_analyses(con, limit=batch_size)

        if not analyses:
            logger.info("no_unrated_analyses")
            return {
                "processed": 0,
                "failed": 0,
                "skipped_low_confidence": 0,
                "skipped_missing_oab": 0,
                "status": "success",
            }

        for analysis in analyses:
            try:
                # Get participants
                winner_oab = analysis["winner_lawyer_oab"]
                winner_state = analysis["winner_lawyer_state"]

                loser_oab = analysis["loser_lawyer_oab"]
                loser_state = analysis["loser_lawyer_state"]

                # Identity is strictly (oab, state); rows missing either are
                # unusable for rating. Mark them as rated so they don't block
                # the queue forever, but count them separately.
                if not winner_oab or not winner_state or not loser_oab or not loser_state:
                    skipped_missing_oab += 1
                    mark_analysis_as_rated(con, analysis["id"])
                    continue

                # Tribunal-segmented rating: each sigla_tribunal is its own
                # "league" so top lawyers at TJSP aren't inflated by wins at
                # a smaller jurisdiction with weaker opposition.
                tribunal = analysis.get("sigla_tribunal") or "GLOBAL"

                # Low-confidence gate: skip matches the classifier isn't
                # sure about; keep the queue moving by marking as rated.
                confidence = analysis.get("confidence_score")
                if confidence is not None and float(confidence) < CONFIDENCE_FLOOR:
                    skipped_low_confidence += 1
                    mark_analysis_as_rated(con, analysis["id"])
                    continue

                # Weight for partial/full updates based on confidence.
                if confidence is None or float(confidence) >= CONFIDENCE_FULL:
                    update_weight = 1.0
                else:
                    update_weight = float(confidence)

                # Get current ratings (per tribunal)
                winner_data = get_lawyer_rating(con, winner_oab, winner_state, tribunal=tribunal)
                loser_data = get_lawyer_rating(con, loser_oab, loser_state, tribunal=tribunal)

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
                        model,
                        mu=winner_data["mu"],
                        sigma=winner_data["sigma"],
                    )
                    winner_wins = winner_data["wins"]
                    winner_losses = winner_data["losses"]
                else:
                    winner_rating = create_rating(model)
                    winner_wins = 0
                    winner_losses = 0

                if loser_data:
                    loser_rating = create_rating(
                        model,
                        mu=loser_data["mu"],
                        sigma=loser_data["sigma"],
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

                # Apply confidence-weighted interpolation for mid-confidence
                # matches. At full confidence this is a no-op; at lower
                # confidence the rating moves only partway to the OpenSkill
                # update, reflecting our uncertainty about the outcome label.
                effective_winner = _interpolate_rating(
                    winner_rating, new_winner[0], update_weight, model
                )
                effective_loser = _interpolate_rating(
                    loser_rating, new_loser[0], update_weight, model
                )

                # Update ratings in DB (per tribunal)
                # Winner
                update_lawyer_rating(
                    con,
                    LawyerRatingUpdate(
                        oab_number=winner_oab,
                        oab_state=winner_state,
                        lawyer_name=winner_name,
                        mu=effective_winner.mu,
                        sigma=effective_winner.sigma,
                        wins=winner_wins + 1,
                        losses=winner_losses,
                        tribunal=tribunal,
                    ),
                )

                # Record winner snapshot
                insert_rating_snapshot(
                    con,
                    RatingSnapshot(
                        advogado_id=f"{winner_oab}:{winner_state}:{tribunal}",
                        comunicacao_id=str(analysis["id"]),
                        oab_number=winner_oab,
                        oab_state=winner_state,
                        mu_before=winner_rating.mu,
                        sigma_before=winner_rating.sigma,
                        mu_after=effective_winner.mu,
                        sigma_after=effective_winner.sigma,
                        wins=winner_wins + 1,
                        losses=winner_losses,
                    ),
                )

                # Loser
                update_lawyer_rating(
                    con,
                    LawyerRatingUpdate(
                        oab_number=loser_oab,
                        oab_state=loser_state,
                        lawyer_name=loser_name,
                        mu=effective_loser.mu,
                        sigma=effective_loser.sigma,
                        wins=loser_wins,
                        losses=loser_losses + 1,
                        tribunal=tribunal,
                    ),
                )

                # Record loser snapshot
                insert_rating_snapshot(
                    con,
                    RatingSnapshot(
                        advogado_id=f"{loser_oab}:{loser_state}:{tribunal}",
                        comunicacao_id=str(analysis["id"]),
                        oab_number=loser_oab,
                        oab_state=loser_state,
                        mu_before=loser_rating.mu,
                        sigma_before=loser_rating.sigma,
                        mu_after=effective_loser.mu,
                        sigma_after=effective_loser.sigma,
                        wins=loser_wins,
                        losses=loser_losses + 1,
                    ),
                )

                # Mark as rated
                mark_analysis_as_rated(con, analysis["id"])
                processed += 1

            except Exception as e:
                logger.exception("rating_failed", analysis_id=analysis["id"], error=str(e))
                failed += 1

        logger.info(
            "rating_calculation_complete",
            processed=processed,
            failed=failed,
            skipped_low_confidence=skipped_low_confidence,
            skipped_missing_oab=skipped_missing_oab,
        )
    except Exception as e:
        logger.exception("rating_pipeline_failed", error=str(e))
        return {
            "processed": processed,
            "failed": failed,
            "skipped_low_confidence": skipped_low_confidence,
            "skipped_missing_oab": skipped_missing_oab,
            "status": "failed",
            "error": str(e),
        }
    else:
        return {
            "processed": processed,
            "failed": failed,
            "skipped_low_confidence": skipped_low_confidence,
            "skipped_missing_oab": skipped_missing_oab,
            "status": "success",
        }
