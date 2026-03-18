"""Rating storage repository."""

from typing import Any

import duckdb
import structlog
from ibis import _
from ibis.backends.duckdb import Backend


logger = structlog.get_logger()


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


def update_lawyer_rating(  # noqa: PLR0913
    con: Backend,
    oab_number: str,
    oab_state: str,
    lawyer_name: str | None,
    mu: float,
    sigma: float,
    wins: int,
    losses: int,
    tribunal: str = "GLOBAL",
) -> None:
    """Update or insert lawyer rating.

    Args:
        con: Database connection.
        oab_number: Lawyer OAB.
        oab_state: Lawyer OAB state.
        lawyer_name: Lawyer name.
        mu: OpenSkill mu.
        sigma: OpenSkill sigma.
        wins: Total wins.
        losses: Total losses.
        tribunal: Optional tribunal code.
    """
    total_cases = wins + losses
    rating = mu - 3 * sigma
    win_rate = (float(wins) / total_cases) if total_cases > 0 else 0.0

    # We use parameter substitution. 'GLOBAL' is default in Python arg,
    # but we should pass it explicitly if None to match schema default logic if needed,
    # or rely on the function caller passing the default.
    # Since we declare it as default arg "GLOBAL", it won't be None unless explicitly passed as None.

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
            oab_number,
            oab_state,
            lawyer_name,
            mu,
            sigma,
            rating,
            win_rate,
            total_cases,
            wins,
            losses,
            tribunal,
        ],
    )


def insert_rating_snapshot(  # noqa: PLR0913
    con: Backend,
    *,
    advogado_id: str,
    comunicacao_id: str,
    oab_number: str,
    oab_state: str,
    mu_before: float,
    sigma_before: float,
    mu_after: float,
    sigma_after: float,
    wins: int,
    losses: int,
) -> None:
    """Record a rating snapshot in ratings_history.

    Called after each OpenSkill update to maintain a full audit trail.

    Args:
        con: Database connection.
        advogado_id: UUIDv5 lawyer ID (OAB+UF based).
        comunicacao_id: Communication that triggered this rating update.
        oab_number: Lawyer OAB number.
        oab_state: Lawyer OAB state.
        mu_before: Mu before this update.
        sigma_before: Sigma before this update.
        mu_after: Mu after this update.
        sigma_after: Sigma after this update.
        wins: Total wins after this update.
        losses: Total losses after this update.
    """
    rating_after = mu_after - 3 * sigma_after

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
                advogado_id,
                comunicacao_id,
                oab_number,
                oab_state,
                mu_before,
                sigma_before,
                mu_after,
                sigma_after,
                rating_after,
                wins,
                losses,
            ],
        )
    except (duckdb.Error, ValueError, TypeError) as e:
        # Non-fatal — don't break the rating pipeline for history logging
        logger.warning(
            "rating_snapshot_failed",
            advogado_id=advogado_id,
            comunicacao_id=comunicacao_id,
            error=str(e),
        )
