"""Analysis repository."""

import asyncio
import contextlib
from datetime import UTC, datetime
from typing import Any

import ibis
from ibis import BaseBackend


class AnalysisRepository:
    """Repository for managing analysis results."""

    def __init__(self, con: BaseBackend) -> None:
        """Initialize the repository.

        Args:
            con: Ibis DuckDB connection backend.
        """
        self.con = con

    def _sync_store_analysis_result(self, result: dict[str, Any]) -> None:
        """Synchronous store analysis result."""
        t = ibis.memtable([result])
        self.con.insert("analysis_results", t)

        # Mark intimation as analyzed so it won't be reprocessed.
        intimation_id = result.get("intimation_id")
        analyzed_at = result.get("analyzed_at")
        if intimation_id is None:
            return

        if analyzed_at is None:
            analyzed_at = datetime.now(UTC)

        with contextlib.suppress(Exception):
            raw_con = self.con.con
            raw_con.execute(
                "UPDATE intimations SET analyzed = TRUE, "
                "analyzed_at = ?, analysis_attempted_at = ? "
                "WHERE id = ?",
                (analyzed_at, analyzed_at, intimation_id),
            )

    async def store_analysis_result(self, result: dict[str, Any]) -> None:
        """Store analysis result.

        Args:
            result: Dict matching analysis_results schema.
        """
        await asyncio.to_thread(self._sync_store_analysis_result, result)

    def _sync_store_analysis_results_batch(self, results: list[dict[str, Any]]) -> None:
        """Synchronous store analysis results in batch."""
        if not results:
            return

        t = ibis.memtable(results)
        self.con.insert("analysis_results", t)

        # Update intimations
        intimation_ids = [r.get("intimation_id") for r in results if r.get("intimation_id")]
        if not intimation_ids:
            return

        analyzed_at = datetime.now(UTC)

        # Batch update using IN clause
        raw_con = self.con.con

        # Generate placeholders
        placeholders = ", ".join(["?"] * len(intimation_ids))
        query = (
            f"UPDATE intimations SET analyzed = TRUE, "
            f"analyzed_at = ?, analysis_attempted_at = ? "
            f"WHERE id IN ({placeholders})"
        )

        params = [analyzed_at, analyzed_at, *intimation_ids]

        with contextlib.suppress(Exception):
            raw_con.execute(query, params)

    async def store_analysis_results_batch(self, results: list[dict[str, Any]]) -> None:
        """Store analysis results in batch.

        Args:
            results: List of Dicts matching analysis_results schema.
        """
        await asyncio.to_thread(self._sync_store_analysis_results_batch, results)

    def _sync_get_unscored_analyses(self, limit: int = 100) -> list[dict[str, Any]]:
        """Synchronous fetch unscored analyses."""
        t_analysis = self.con.table("analysis_results")

        try:
            # Filter where scored is null or false, AND lawyers are identified
            unscored = t_analysis.filter(
                (t_analysis.scored.isnull()) | (~t_analysis.scored),
            ).filter(
                t_analysis.winner_lawyer_oab.notnull() & t_analysis.loser_lawyer_oab.notnull(),
            ).limit(limit)
            return unscored.execute().to_dict(orient="records")
        except Exception:
            return []

    async def get_unscored_analyses(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch unscored analyses."""
        return await asyncio.to_thread(self._sync_get_unscored_analyses, limit)

    def _sync_mark_analyses_scored(self, ids: list[Any]) -> None:
        """Mark analyses as scored."""
        if not ids:
            return
        raw_con = self.con.con
        placeholders = ", ".join(["?"] * len(ids))

        query = f"UPDATE analysis_results SET scored = TRUE WHERE id IN ({placeholders})"  # noqa: S608
        raw_con.execute(query, ids)

    async def mark_analyses_scored(self, ids: list[Any]) -> None:
        """Mark analyses as scored."""
        await asyncio.to_thread(self._sync_mark_analyses_scored, ids)
