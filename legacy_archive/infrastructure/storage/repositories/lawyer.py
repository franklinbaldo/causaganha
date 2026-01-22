"""Lawyer rating repository."""

import asyncio
from typing import Any

from ibis import BaseBackend


class LawyerRatingRepository:
    """Repository for managing lawyer ratings."""

    def __init__(self, con: BaseBackend) -> None:
        """Initialize the repository.

        Args:
            con: Ibis DuckDB connection backend.
        """
        self.con = con

    def _sync_get_lawyer_ratings(self, oabs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        """Fetch ratings for a list of lawyers (oab, state)."""
        if not oabs:
            return []

        t_ratings = self.con.table("lawyer_ratings")
        numbers = [x[0] for x in oabs]
        states = [x[1] for x in oabs]

        try:
            candidates = (
                t_ratings.filter(
                    t_ratings.oab_number.isin(numbers) & t_ratings.oab_state.isin(states),
                )
                .execute()
                .to_dict(orient="records")
            )
        except Exception:
            return []

        target_set = set(oabs)
        return [r for r in candidates if (r["oab_number"], r["oab_state"]) in target_set]

    async def get_lawyer_ratings(self, oabs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        """Fetch ratings for a list of lawyers."""
        return await asyncio.to_thread(self._sync_get_lawyer_ratings, oabs)

    def _sync_save_lawyer_ratings(self, ratings: list[dict[str, Any]]) -> None:
        """Save updated lawyer ratings."""
        if not ratings:
            return

        raw_con = self.con.con
        for r in ratings:
            raw_con.execute(
                """
                INSERT INTO lawyer_ratings (
                    oab_number, oab_state, lawyer_name,
                    mu, sigma, last_updated,
                    total_cases, wins, losses
                ) VALUES (
                    ?, ?, ?,
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
            """,
                [
                    r["oab_number"],
                    r["oab_state"],
                    r.get("lawyer_name"),
                    r["mu"],
                    r["sigma"],
                    r["total_cases"],
                    r["wins"],
                    r["losses"],
                ],
            )

    async def save_lawyer_ratings(self, ratings: list[dict[str, Any]]) -> None:
        """Save updated lawyer ratings."""
        await asyncio.to_thread(self._sync_save_lawyer_ratings, ratings)
