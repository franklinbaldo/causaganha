"""Intimation repository."""

import asyncio
import contextlib
from typing import Any

import ibis
from ibis import BaseBackend

from causaganha.domain.models import Intimation


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

        data = [self._intimation_to_db(i) for i in intimations]

        # Using native DuckDB connection for UPSERT (ON CONFLICT) support
        # Ibis insert() doesn't support ON CONFLICT yet
        raw_con = self.con.con

        # 1. Insert Intimations
        for item in data:
            # We construct the query manually for now to support ON CONFLICT
            # Note: In a real scenario with many rows, we would use executemany or appender
            # But for simplicity and correctness with ON CONFLICT:
            keys = list(item.keys())
            placeholders = ", ".join(["?" for _ in keys])
            columns = ", ".join(keys)

            sql = f"""
                INSERT INTO intimations ({columns})
                VALUES ({placeholders})
                ON CONFLICT (id) DO UPDATE SET
                    updated_at = now(),
                    status = excluded.status
            """
            try:
                raw_con.execute(sql, list(item.values()))
            except Exception as e:
                # Log error but continue? Or raise?
                # Ideally we want to fail if DB is broken, but maybe skip bad rows?
                # For now let's raise to see issues in tests
                raise e

        # 2. Insert Lawyers
        for intimation in intimations:
            for lawyer in intimation.advogados:
                sql_lawyer = """
                    INSERT OR IGNORE INTO intimation_lawyers
                    (intimation_id, oab_number, oab_state, lawyer_name, polo)
                    VALUES (?, ?, ?, ?, ?)
                """
                raw_con.execute(sql_lawyer, [
                    intimation.id,
                    lawyer.numero_oab,
                    lawyer.uf_oab,
                    lawyer.nome,
                    "A" # Default polo
                ])

    async def store_intimations(self, intimations: list[Intimation]) -> None:
        """Store a list of intimations in the database asynchronously.

        Args:
            intimations: List of Intimation objects to store.
        """
        await asyncio.to_thread(self._sync_store_intimations, intimations)

    def _sync_get_unanalyzed_intimations(self, limit: int = 100) -> list[Intimation]:
        """Synchronous implementation of fetching unanalyzed intimations."""
        t_int = self.con.table("intimations")

        # Check 'analyzed' flag in 'intimations' table.
        # Use ~t_int.analyzed for negation instead of 'not' keyword
        filtered = t_int.filter(t_int.analyzed.isnull() | (~t_int.analyzed))

        # Verify we only fetch rows that have a link (to download PDF)
        filtered = filtered.filter(t_int.link.notnull())

        query = filtered.limit(limit)

        records = query.execute().to_dict(orient="records")
        return [Intimation(**record) for record in records]

    async def get_unanalyzed_intimations(self, limit: int = 100) -> list[Intimation]:
        """Fetch intimations that have not been analyzed yet.

        Args:
            limit: Max number of records to fetch.

        Returns:
            List of Intimation objects.
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
