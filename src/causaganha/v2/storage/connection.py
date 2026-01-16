"""DuckDB connection via Ibis."""

from pathlib import Path

import ibis
import structlog
from ibis.backends.duckdb import Backend


logger = structlog.get_logger()

_connection: Backend | None = None


def get_connection(
    db_path: str = "data/causaganha.duckdb",
) -> Backend:
    """Get or create DuckDB connection via Ibis.

    This is a singleton - returns the same connection instance.
    """
    global _connection  # noqa: PLW0603

    if _connection is None:
        if db_path != ":memory:":
            db_file = Path(db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            logger.info("connecting_to_duckdb", path=str(db_file))
            _connection = ibis.duckdb.connect(str(db_file))
        else:
            logger.info("connecting_to_duckdb_memory")
            _connection = ibis.duckdb.connect(db_path)

        # Initialize schema if needed
        _initialize_schema(_connection)

    return _connection


def _initialize_schema(con: Backend) -> None:
    """Create tables if they don't exist."""
    tables = con.list_tables()

    if "intimations" not in tables:
        logger.info("creating_schema")

        # Read schema from SQL file
        schema_file = Path(__file__).parent / "schema.sql"
        if schema_file.exists():
            schema_sql = schema_file.read_text()
            # Execute each statement
            for statement in schema_sql.split(";"):
                if statement.strip():
                    con.raw_sql(statement)
        else:
            logger.warning("schema_file_not_found", path=str(schema_file))
