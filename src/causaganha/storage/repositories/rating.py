"""Rating storage repository."""

from dataclasses import dataclass
from typing import Any

import duckdb
import structlog
from ibis import _
from ibis.backends.duckdb import Backend


logger = structlog.get_logger()


# Minimum wins + losses before a lawyer is considered "ranked enough" to show
# on any public leaderboard. Below this threshold the OpenSkill sigma is still
# too wide to produce a meaningful ordering.
MIN_MATCHES_FOR_LEADERBOARD = 20


@dataclass
class LawyerRatingUpdate:
    """Data required to update or insert a lawyer's rating."""

    oab_number: str
    oab_state: str
    lawyer_name: str | None
    mu: float
    sigma: float
    wins: int
    losses: int
    tribunal: str = "GLOBAL"


@dataclass
class RatingSnapshot:
    """Data required to record a rating history snapshot."""

    advogado_id: str
    comunicacao_id: str
    oab_number: str
    oab_state: str
    mu_before: float
    sigma_before: float
    mu_after: float
    sigma_after: float
    wins: int
    losses: int


def get_lawyer_rating(
    con: Backend,
    oab_number: str,
    oab_state: str,
    tribunal: str = "GLOBAL",
) -> dict[str, Any] | None:
    """Get current rating for a lawyer.

    Args:
        con: Database connection.
        oab_number: Lawyer OAB.
        oab_state: Lawyer OAB state.
        tribunal: Optional tribunal code.

    Returns:
        Dictionary with rating info or None if not found.
    """
    ratings = con.table("lawyer_ratings")

    query = (
        ratings.filter(_.oab_number == oab_number)
        .filter(_.oab_state == oab_state)
        .filter(_.tribunal == tribunal)
    )

    result = query.to_pandas()

    if result.empty:
        return None

    return result.iloc[0].to_dict()


def update_lawyer_rating(con: Backend, update: LawyerRatingUpdate) -> None:
    """Update or insert lawyer rating.

    Args:
        con: Database connection.
        update: Rating data to write.
    """
    total_cases = update.wins + update.losses
    rating = update.mu - 3 * update.sigma
    win_rate = (float(update.wins) / total_cases) if total_cases > 0 else 0.0

    con.con.execute(
        """
        INSERT INTO lawyer_ratings (
            oab_number, oab_state, lawyer_name,
            mu, sigma,
            rating, win_rate,
            total_cases, wins, losses,
            tribunal,
            last_updated
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW()
        )
        ON CONFLICT (oab_number, oab_state, tribunal) DO UPDATE SET
            mu = EXCLUDED.mu,
            sigma = EXCLUDED.sigma,
            rating = EXCLUDED.rating,
            win_rate = EXCLUDED.win_rate,
            total_cases = EXCLUDED.total_cases,
            wins = EXCLUDED.wins,
            losses = EXCLUDED.losses,
            last_updated = NOW()
        """,
        [
            update.oab_number,
            update.oab_state,
            update.lawyer_name,
            update.mu,
            update.sigma,
            rating,
            win_rate,
            total_cases,
            update.wins,
            update.losses,
            update.tribunal,
        ],
    )


def list_leaderboard(
    con: Backend,
    tribunal: str,
    *,
    limit: int = 100,
    min_matches: int = MIN_MATCHES_FOR_LEADERBOARD,
) -> list[dict[str, Any]]:
    """Return the public leaderboard for a tribunal.

    This is the read path for anything user-facing. It only exposes lawyers
    with enough match history (``wins + losses >= min_matches``) and returns
    the *conservative* rating (``mu - 3*sigma``) — raw mu/sigma are considered
    internals and intentionally omitted here to prevent a future consumer from
    accidentally ordering by a confidence-inflated score.

    Args:
        con: Database connection.
        tribunal: Tribunal code ("GLOBAL" for the cross-league rating).
        limit: Max rows to return.
        min_matches: Minimum (wins + losses) required to appear.

    Returns:
        List of dicts with oab_number, oab_state, lawyer_name, rating,
        total_cases, wins, losses, win_rate, tribunal.
    """
    ratings = con.table("lawyer_ratings")

    query = (
        ratings.filter(_.tribunal == tribunal)
        .filter((_.wins + _.losses) >= min_matches)
        .select(
            _.oab_number,
            _.oab_state,
            _.lawyer_name,
            _.rating,
            _.total_cases,
            _.wins,
            _.losses,
            _.win_rate,
            _.tribunal,
        )
        .order_by(_.rating.desc())
        .limit(limit)
    )

    result = query.to_pandas()
    if result.empty:
        return []
    return result.to_dict("records")


def insert_rating_snapshot(con: Backend, snapshot: RatingSnapshot) -> None:
    """Record a rating snapshot in ratings_history.

    Called after each OpenSkill update to maintain a full audit trail.

    Args:
        con: Database connection.
        snapshot: Snapshot data to record.
    """
    rating_after = snapshot.mu_after - 3 * snapshot.sigma_after

    try:
        con.con.execute(
            """
            INSERT INTO ratings_history (
                advogado_id, comunicacao_id,
                oab_number, oab_state,
                mu_before, sigma_before,
                mu_after, sigma_after, rating_after,
                wins, losses
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (advogado_id, comunicacao_id) DO NOTHING
            """,
            [
                snapshot.advogado_id,
                snapshot.comunicacao_id,
                snapshot.oab_number,
                snapshot.oab_state,
                snapshot.mu_before,
                snapshot.sigma_before,
                snapshot.mu_after,
                snapshot.sigma_after,
                rating_after,
                snapshot.wins,
                snapshot.losses,
            ],
        )
    except (duckdb.Error, ValueError, TypeError) as e:
        # Non-fatal — don't break the rating pipeline for history logging
        logger.warning(
            "rating_snapshot_failed",
            advogado_id=snapshot.advogado_id,
            comunicacao_id=snapshot.comunicacao_id,
            error=str(e),
        )
