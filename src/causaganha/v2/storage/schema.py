"""Database schema definitions."""

import asyncio

import ibis
from ibis import BaseBackend


async def create_schema(con: BaseBackend) -> None:
    """Create the database schema if it doesn't exist.

    Args:
        con: Ibis DuckDB connection backend.
    """
    def _sync_create_schema() -> None:
        tables = con.list_tables()

        if "pipeline_state" not in tables:
            con.create_table(
                "pipeline_state",
                schema=ibis.schema({
                    "task_id": "string",
                    "step": "string",
                    "timestamp": "timestamp",
                }),
            )

        if "intimations" not in tables:
            con.create_table(
                "intimations",
                schema=ibis.schema({
                    "id": "int64",
                    "numero_processo": "string",
                    "data_disponibilizacao": "string",
                    "sigla_tribunal": "string",
                    "tipo_comunicacao": "string",
                    "nome_orgao": "string",
                    "texto": "string",
                    "link": "string",
                    "tipo_documento": "string",
                    "nome_classe": "string",
                    "hash": "string",
                    "status": "string",
                    "created_at": "timestamp",
                }),
            )

    await asyncio.to_thread(_sync_create_schema)
