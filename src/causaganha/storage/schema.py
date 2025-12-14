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
                # Additional fields from DecisionAnalysis model
                "winner_lawyer_oab": "string",
                "winner_lawyer_state": "string",
                "winner_party_name": "string",
                "loser_lawyer_oab": "string",
                "loser_lawyer_state": "string",
                "loser_party_name": "string",
                "decision_type": "string",
                "decision_reasoning": "string",
                "scored": "boolean",
            }),
        )

    if "lawyer_ratings" not in con.list_tables():
        con.create_table(
            "lawyer_ratings",
            schema=ibis.schema({
                "oab_number": "string",
                "oab_state": "string",
                "lawyer_name": "string",
                "mu": "float64",
                "sigma": "float64",
                "last_updated": "timestamp",
                "total_cases": "int64",
                "wins": "int64",
                "losses": "int64",
            }),
        )
        con.raw_sql("CREATE UNIQUE INDEX IF NOT EXISTS idx_lawyer_ratings_unique ON lawyer_ratings (oab_number, oab_state)")
