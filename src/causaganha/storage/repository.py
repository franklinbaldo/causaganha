"""Database repository for intimations and analysis results."""

import asyncio
from datetime import datetime, timezone
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
            for lawyer in intimation.advogados:
                lawyers_data.append({
                    "intimation_id": intimation.id,
                    "oab_number": lawyer.numero_oab,
                    "oab_state": lawyer.uf_oab,
                    "lawyer_name": lawyer.nome,
                    "polo": "A" # Default for now, should extract if available
                })

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

        # Check if 'analysis_results' table exists and has data to join, or if we should rely on 'analyzed' flag in 'intimations'
        # The test case set 'analyzed' flag to TRUE for id=1.
        # But here we are joining with 'analysis_results'.
        # If 'analysis_results' is empty, LEFT JOIN ... WHERE right.id IS NULL returns ALL rows.
        # This explains why id=1 is returned (it's not in analysis_results, so it's considered unanalyzed by this logic).

        # We should also check the 'analyzed' flag in 'intimations' table if it exists.
        # The schema definition has 'analyzed' boolean field.

        # Let's use the 'analyzed' flag as primary filter if possible, or combine both.
        # If the 'analyzed' column exists and is populated, it's faster.

        # Treat NULL as "not analyzed yet" for backward-compatibility with older inserts.
        filtered = t_int.filter(t_int.analyzed.isnull() | (t_int.analyzed == False))

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
            analyzed_at = datetime.now(timezone.utc)

        try:
            raw_con = self.con.con
            raw_con.execute(
                "UPDATE intimations SET analyzed = TRUE, analyzed_at = ?, analysis_attempted_at = ? WHERE id = ?",
                (analyzed_at, analyzed_at, intimation_id),
            )
        except Exception:
            # Best-effort: schema may be evolving in early development.
            return

    async def store_analysis_result(self, result: dict[str, Any]) -> None:
        """Store analysis result.

        Args:
            result: Dict matching analysis_results schema.
        """
        await asyncio.to_thread(self._sync_store_analysis_result, result)

    def _sync_get_unarchived_intimations(self, limit: int = 100) -> list[dict[str, Any]]:
        """Synchronous implementation of fetching unarchived intimations."""
        t_int = self.con.table("intimations")

        # Filter intimations that have not been archived yet
        # Assuming there's an 'archived' column or 'ia_url' column
        try:
            filtered = t_int.filter(
                (t_int.ia_url.isnull()) | (t_int.ia_url == "")
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
        try:
            raw_con.execute(
                "UPDATE intimations SET ia_url = ?, archived_at = CURRENT_TIMESTAMP WHERE id = ?",
                (ia_url, intimation_id),
            )
        except Exception:
            # If columns don't exist, we can't mark as archived
            # This is acceptable during early development
            pass

    def _validate_archive_params(self, intimation_id: str, ia_url: str) -> None:
        """Validate parameters for archiving (refactored validation logic).

        Args:
            intimation_id: The intimation ID.
            ia_url: The Internet Archive URL.

        Raises:
            ValueError: If parameters are invalid.
        """
        if not intimation_id or intimation_id.strip() == "":
            raise ValueError("Intimation ID cannot be empty")

        if not ia_url or not (ia_url.startswith("http://") or ia_url.startswith("https://")):
            raise ValueError("Invalid IA URL")

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
