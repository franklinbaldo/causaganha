"""Database repository for intimations and analysis results."""

import asyncio
import contextlib
from datetime import UTC, datetime
from typing import Any

import ibis
from ibis import BaseBackend

from causaganha.domain.models import Intimation


class IntimationRepository:
    """Repository for managing intimation data and analysis results."""

    def __init__(self, con: BaseBackend) -> None:
        """Initialize the repository.

        Args:
            con: Ibis DuckDB connection backend.
        """
        self.con = con

    def _intimation_to_db(self, intimation: Intimation) -> dict[str, object]:
        """Convert Intimation model to database schema dict."""
        return {
            "id": intimation.id,
            "numero_processo": intimation.numero_processo,
            "data_disponibilizacao": intimation.data_disponibilizacao.isoformat(),
            "sigla_tribunal": intimation.sigla_tribunal,
            "tipo_comunicacao": intimation.tipo_comunicacao,
            "nome_orgao": intimation.nome_orgao,
            "texto": intimation.texto,
            "link": intimation.link,
            "tipo_documento": intimation.tipo_documento,
            "nome_classe": intimation.nome_classe,
            "codigo_classe": intimation.codigo_classe,
            "hash": intimation.hash,
            "status": intimation.status,
            # Pipeline tracking defaults
            "analyzed": False,
            "analysis_attempted_at": None,
            "analysis_error": None,
            "analyzed_at": None,
            "ia_url": None,
            "archived_at": None,
            "needs_download": True,
        }

    def _sync_store_intimations(self, intimations: list[Intimation]) -> None:
        """Synchronous implementation of storing intimations."""
        if not intimations:
            return

        data = [self._intimation_to_db(i) for i in intimations]

        # Using memtable to insert data
        t = ibis.memtable(data)
        self.con.insert("intimations", t)

        # Also store lawyers if present
        lawyers_data = []
        for intimation in intimations:
            lawyers_data.extend([
                {
                    "intimation_id": intimation.id,
                    "oab_number": lawyer.numero_oab,
                    "oab_state": lawyer.uf_oab,
                    "lawyer_name": lawyer.nome,
                    "polo": "A",  # Default for now, should extract if available
                }
                for lawyer in intimation.advogados
            ])

        if lawyers_data:
            t_lawyers = ibis.memtable(lawyers_data)
            self.con.insert("intimation_lawyers", t_lawyers)

    async def store_intimations(self, intimations: list[Intimation]) -> None:
        """Store a list of intimations in the database asynchronously.

        Args:
            intimations: List of Intimation objects to store.
        """
        await asyncio.to_thread(self._sync_store_intimations, intimations)

    def _sync_get_unanalyzed_intimations(self, limit: int = 100) -> list[dict[str, Any]]:
        """Synchronous implementation of fetching unanalyzed intimations."""
        t_int = self.con.table("intimations")

        # Check 'analyzed' flag in 'intimations' table.
        # Use ~t_int.analyzed for negation instead of 'not' keyword
        filtered = t_int.filter(t_int.analyzed.isnull() | (~t_int.analyzed))

        # Verify we only fetch rows that have a link (to download PDF)
        filtered = filtered.filter(t_int.link.notnull())

        query = filtered.limit(limit)

        return query.execute().to_dict(orient="records")

    async def get_unanalyzed_intimations(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch intimations that have not been analyzed yet.

        Args:
            limit: Max number of records to fetch.

        Returns:
            List of dicts representing intimations.
        """
        return await asyncio.to_thread(self._sync_get_unanalyzed_intimations, limit)

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
        )  # noqa: S608

        params = [analyzed_at, analyzed_at, *intimation_ids]

        with contextlib.suppress(Exception):
            raw_con.execute(query, params)

    async def store_analysis_results_batch(self, results: list[dict[str, Any]]) -> None:
        """Store analysis results in batch.

        Args:
            results: List of Dicts matching analysis_results schema.
        """
        await asyncio.to_thread(self._sync_store_analysis_results_batch, results)

    def _sync_get_unarchived_intimations(self, limit: int = 100) -> list[dict[str, Any]]:
        """Synchronous implementation of fetching unarchived intimations."""
        t_int = self.con.table("intimations")

        # Filter intimations that have not been archived yet
        try:
            filtered = t_int.filter(
                (t_int.ia_url.isnull()) | (t_int.ia_url == ""),
            ).filter(t_int.link.notnull())
        except Exception:
            # If ia_url column doesn't exist, just get all with links
            filtered = t_int.filter(t_int.link.notnull())

        query = filtered.limit(limit)
        return query.execute().to_dict(orient="records")

    async def get_unarchived_intimations(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch intimations that have not been archived yet.

        Args:
            limit: Max number of records to fetch.

        Returns:
            List of dicts representing intimations.
        """
        return await asyncio.to_thread(self._sync_get_unarchived_intimations, limit)

    def _sync_mark_as_archived(self, intimation_id: str, ia_url: str) -> None:
        """Synchronous mark intimation as archived."""
        raw_con = self.con.con
        with contextlib.suppress(Exception):
            raw_con.execute(
                "UPDATE intimations SET ia_url = ?, archived_at = CURRENT_TIMESTAMP WHERE id = ?",
                (ia_url, intimation_id),
            )

    def _validate_archive_params(self, intimation_id: str, ia_url: str) -> None:
        """Validate parameters for archiving (refactored validation logic).

        Args:
            intimation_id: The intimation ID.
            ia_url: The Internet Archive URL.

        Raises:
            ValueError: If parameters are invalid.
        """
        if not intimation_id or intimation_id.strip() == "":
            msg = "Intimation ID cannot be empty"
            raise ValueError(msg)

        if not ia_url or not (ia_url.startswith(("http://", "https://"))):
            msg = "Invalid IA URL"
            raise ValueError(msg)

    async def mark_as_archived(self, intimation_id: str, ia_url: str) -> None:
        """Mark an intimation as archived.

        Args:
            intimation_id: The intimation ID.
            ia_url: The Internet Archive URL.

        Raises:
            ValueError: If intimation_id is empty or ia_url is invalid.
        """
        # Validate inputs (TDD-driven improvement, refactored)
        self._validate_archive_params(intimation_id, ia_url)

        await asyncio.to_thread(self._sync_mark_as_archived, intimation_id, ia_url)

    def _sync_get_all_intimations(self, limit: int = 100) -> list[dict[str, Any]]:
        """Synchronous implementation of fetching all intimations."""
        t_int = self.con.table("intimations")
        query = t_int.limit(limit)
        return query.execute().to_dict(orient="records")

    async def get_all_intimations(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch all intimations.

        Args:
            limit: Max number of records to fetch.

        Returns:
            List of dicts representing intimations.
        """
        return await asyncio.to_thread(self._sync_get_all_intimations, limit)

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

    def _sync_get_lawyer_ratings(self, oabs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        """Fetch ratings for a list of lawyers (oab, state)."""
        if not oabs:
            return []

        t_ratings = self.con.table("lawyer_ratings")
        numbers = [x[0] for x in oabs]
        states = [x[1] for x in oabs]

        try:
            candidates = t_ratings.filter(
                t_ratings.oab_number.isin(numbers) & t_ratings.oab_state.isin(states),
            ).execute().to_dict(orient="records")
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
            raw_con.execute("""
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
            """, [
                r["oab_number"], r["oab_state"], r.get("lawyer_name"),
                r["mu"], r["sigma"],
                r["total_cases"], r["wins"], r["losses"],
            ])

    async def save_lawyer_ratings(self, ratings: list[dict[str, Any]]) -> None:
        """Save updated lawyer ratings."""
        await asyncio.to_thread(self._sync_save_lawyer_ratings, ratings)

    def _sync_mark_analyses_scored(self, ids: list[Any]) -> None:
        """Mark analyses as scored."""
        if not ids:
            return
        raw_con = self.con.con
        placeholders = ", ".join(["?"] * len(ids))
        # noqa: S608 - Internal IDs are safe for simple interpolation here
        query = f"UPDATE analysis_results SET scored = TRUE WHERE id IN ({placeholders})"
        raw_con.execute(query, ids)

    async def mark_analyses_scored(self, ids: list[Any]) -> None:
        """Mark analyses as scored."""
        await asyncio.to_thread(self._sync_mark_analyses_scored, ids)
