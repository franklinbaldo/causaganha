"""Database repository for intimations and analysis results."""

import asyncio
from datetime import UTC, datetime, date
from typing import Any

import ibis
from ibis import BaseBackend

from causaganha.domain.models import Intimation, Lawyer


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
            "analyzed": intimation.analyzed,
            "analysis_attempted_at": intimation.analysis_attempted_at,
            "analysis_error": intimation.analysis_error,
            "analyzed_at": intimation.analyzed_at,
            "ia_url": intimation.ia_url,
            "archived_at": intimation.archived_at,
            "needs_download": intimation.needs_download,
        }

    def _row_to_intimation(self, row: dict[str, Any]) -> Intimation:
        """Convert database row to Intimation model."""
        # Handle date parsing
        data_disp = row.get("data_disponibilizacao")
        if isinstance(data_disp, str):
            try:
                data_disp = date.fromisoformat(data_disp)
            except ValueError:
                data_disp = date.today() # Fallback? Or raise?
        elif not isinstance(data_disp, date):
            # If it's None or something else, we need a default or handle error
            # For now, let's assume valid data or default to today if missing (unlikely if DB enforces)
            data_disp = date.today()

        return Intimation(
            id=row["id"],
            numero_processo=row["numero_processo"],
            data_disponibilizacao=data_disp,
            sigla_tribunal=row["sigla_tribunal"],
            tipo_comunicacao=row.get("tipo_comunicacao", ""),
            nome_orgao=row.get("nome_orgao", ""),
            texto=row.get("texto", ""),
            link=row.get("link"),
            tipo_documento=row.get("tipo_documento", ""),
            nome_classe=row.get("nome_classe", ""),
            codigo_classe=row.get("codigo_classe"),
            hash=row.get("hash", ""),
            status=row.get("status"),
            # Pipeline tracking
            analyzed=bool(row.get("analyzed", False)),
            analysis_attempted_at=row.get("analysis_attempted_at"),
            analysis_error=row.get("analysis_error"),
            analyzed_at=row.get("analyzed_at"),
            ia_url=row.get("ia_url"),
            archived_at=row.get("archived_at"),
            needs_download=bool(row.get("needs_download", True)),
            # Relationships are loaded separately if needed
            advogados=[],
            partes=[]
        )

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
                    "polo": "A", # Default for now, should extract if available
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

    def _sync_get_unanalyzed_intimations(self, limit: int = 100) -> list[Intimation]:
        """Synchronous implementation of fetching unanalyzed intimations."""
        t_int = self.con.table("intimations")

        filtered = t_int.filter(t_int.analyzed.isnull() | (t_int.analyzed == False))

        # Verify we only fetch rows that have a link (to download PDF)
        filtered = filtered.filter(t_int.link.notnull())

        query = filtered.limit(limit)
        rows = query.execute().to_dict(orient="records")

        return [self._row_to_intimation(row) for row in rows]

    async def get_unanalyzed_intimations(self, limit: int = 100) -> list[Intimation]:
        """Fetch intimations that have not been analyzed yet.

        Args:
            limit: Max number of records to fetch.

        Returns:
            List of Intimation objects.
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
        query = f"UPDATE intimations SET analyzed = TRUE, analyzed_at = ?, analysis_attempted_at = ? WHERE id IN ({placeholders})"

        params = [analyzed_at, analyzed_at] + intimation_ids

        try:
            raw_con.execute(query, params)
        except Exception:
            pass

    async def store_analysis_results_batch(self, results: list[dict[str, Any]]) -> None:
        """Store analysis results in batch.

        Args:
            results: List of Dicts matching analysis_results schema.
        """
        await asyncio.to_thread(self._sync_store_analysis_results_batch, results)

    def _sync_get_unarchived_intimations(self, limit: int = 100) -> list[Intimation]:
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
        rows = query.execute().to_dict(orient="records")
        return [self._row_to_intimation(row) for row in rows]

    async def get_unarchived_intimations(self, limit: int = 100) -> list[Intimation]:
        """Fetch intimations that have not been archived yet.

        Args:
            limit: Max number of records to fetch.

        Returns:
            List of Intimation objects.
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

    def _sync_get_all_intimations(self, limit: int = 100) -> list[Intimation]:
        """Synchronous implementation of fetching all intimations."""
        t_int = self.con.table("intimations")
        query = t_int.limit(limit)
        rows = query.execute().to_dict(orient="records")
        return [self._row_to_intimation(row) for row in rows]

    async def get_all_intimations(self, limit: int = 100) -> list[Intimation]:
        """Fetch all intimations.

        Args:
            limit: Max number of records to fetch.

        Returns:
            List of Intimation objects.
        """
        return await asyncio.to_thread(self._sync_get_all_intimations, limit)

    def _sync_get_unscored_analyses(self, limit: int = 100) -> list[dict[str, Any]]:
        """Synchronous fetch unscored analyses."""
        t_analysis = self.con.table("analysis_results")

        try:
            # Filter where scored is null or false, AND lawyers are identified
            unscored = t_analysis.filter(
                (t_analysis.scored.isnull()) | (t_analysis.scored == False),
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
        raw_con.execute(f"UPDATE analysis_results SET scored = TRUE WHERE id IN ({placeholders})", ids)

    async def mark_analyses_scored(self, ids: list[Any]) -> None:
        """Mark analyses as scored."""
        await asyncio.to_thread(self._sync_mark_analyses_scored, ids)
