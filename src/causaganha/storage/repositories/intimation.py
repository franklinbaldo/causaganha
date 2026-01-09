"""Intimation repository."""

import asyncio
import contextlib
from typing import Any
import structlog

import ibis
from ibis import BaseBackend

from causaganha.domain.models import Intimation

logger = structlog.get_logger()

class IntimationRepository:
    """Repository for managing intimation data."""

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

        raw_con = self.con.con

        for intimation in intimations:
            try:
                # Prepare statement for intimation
                # We use parameterized query to avoid injection
                raw_con.execute("""
                    INSERT INTO intimations (
                        id, numero_processo, data_disponibilizacao, sigla_tribunal,
                        tipo_comunicacao, nome_orgao, texto, link,
                        tipo_documento, nome_classe, codigo_classe,
                        hash, status, analyzed, needs_download
                    ) VALUES (
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?
                    ) ON CONFLICT (id) DO UPDATE SET
                        updated_at = now()
                """, [
                    intimation.id, intimation.numero_processo, intimation.data_disponibilizacao, intimation.sigla_tribunal,
                    intimation.tipo_comunicacao, intimation.nome_orgao, intimation.texto, intimation.link,
                    intimation.tipo_documento, intimation.nome_classe, intimation.codigo_classe,
                    intimation.hash, intimation.status, False, True
                ])

                # Store lawyers
                for lawyer in intimation.advogados:
                    raw_con.execute("""
                        INSERT INTO intimation_lawyers (
                            intimation_id, oab_number, oab_state, lawyer_name, polo
                        ) VALUES (
                            ?, ?, ?, ?, ?
                        ) ON CONFLICT (intimation_id, oab_number, oab_state) DO NOTHING
                    """, [
                        intimation.id, lawyer.numero_oab, lawyer.uf_oab, lawyer.nome, "A"
                    ])

            except Exception as e:
                logger.exception("store_intimation_failed", error=str(e), intimation_id=intimation.id)

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
        """Validate parameters for archiving.

        Args:
            intimation_id: The intimation ID.
            ia_url: The Internet Archive URL.

        Raises:
            ValueError: If parameters are invalid.
        """
        if not intimation_id or str(intimation_id).strip() == "":
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
