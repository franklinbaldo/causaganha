"""Database schema definitions."""

import ibis
from ibis import BaseBackend


def create_schema(con: BaseBackend) -> None:
    """Create the database schema if it doesn't exist.

    Args:
        con: Ibis DuckDB connection backend.
    """
    if "pipeline_state" not in con.list_tables():
        con.create_table(
            "pipeline_state",
            schema=ibis.schema({
                "task_id": "string",
                "step": "string",
                "timestamp": "timestamp",
            }),
        )

    if "intimations" not in con.list_tables():
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
                "codigo_classe": "string",
                "hash": "string",
                "status": "string",
            }),
        )

    if "analysis_results" not in con.list_tables():
        con.create_table(
            "analysis_results",
            schema=ibis.schema({
                "id": "int64", # Auto-increment usually handled by DuckDB sequence, but for now int64
                "intimation_id": "int64",
                "outcome": "string",
                "summary": "string",
                "judge_name": "string",
                "confidence_score": "float64",
                "analyzed_at": "timestamp",
            }),
        )
