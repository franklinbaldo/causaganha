"""Database schema creation (refactored with TDD)."""

from ibis import BaseBackend

from causaganha.storage.schema_definitions import (
    ANALYSIS_RESULTS_SCHEMA,
    INTIMATION_LAWYERS_SCHEMA,
    INTIMATIONS_SCHEMA,
    LAWYER_RATINGS_SCHEMA,
    PIPELINE_STATE_SCHEMA,
)


def create_schema(con: BaseBackend) -> None:
    """Create the database schema if it doesn't exist.

    Uses schema definitions from schema_definitions module for maintainability.
    Schema includes archive tracking columns (ia_url, archived_at) added via TDD.

    Args:
        con: Ibis DuckDB connection backend.
    """
    # Create tables if they don't exist
    if "pipeline_state" not in con.list_tables():
        con.create_table("pipeline_state", schema=PIPELINE_STATE_SCHEMA)

    if "intimations" not in con.list_tables():
        con.create_table("intimations", schema=INTIMATIONS_SCHEMA)

    # Create unique index on id for UPSERT operations
    # Moved outside to ensure it exists even if table already existed
    con.raw_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_intimations_id ON intimations (id)",
    )
    # Create index on ia_url for faster unarchived queries
    con.raw_sql(
        "CREATE INDEX IF NOT EXISTS idx_intimations_ia_url ON intimations (ia_url)",
    )

    if "intimation_lawyers" not in con.list_tables():
        con.create_table("intimation_lawyers", schema=INTIMATION_LAWYERS_SCHEMA)

    con.raw_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_intimation_lawyers_unique "
        "ON intimation_lawyers (intimation_id, oab_number, oab_state)",
    )

    if "analysis_results" not in con.list_tables():
        con.create_table("analysis_results", schema=ANALYSIS_RESULTS_SCHEMA)

    if "lawyer_ratings" not in con.list_tables():
        con.create_table("lawyer_ratings", schema=LAWYER_RATINGS_SCHEMA)

    con.raw_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_lawyer_ratings_unique "
        "ON lawyer_ratings (oab_number, oab_state)",
    )
