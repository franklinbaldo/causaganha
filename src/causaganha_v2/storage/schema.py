import ibis
from ibis import BaseBackend

def create_schema(con: BaseBackend):
    """
    Create the database schema if it doesn't exist.

    Args:
        con: Ibis DuckDB connection backend.
    """
    if "pipeline_state" not in con.list_tables():
        con.create_table(
            "pipeline_state",
            schema=ibis.schema({
                "task_id": "string",
                "step": "string",
                "timestamp": "timestamp"
            })
        )
