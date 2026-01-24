from typing import Any

from ibis import _
from ibis.backends.duckdb import Backend


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


def update_lawyer_rating(
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
