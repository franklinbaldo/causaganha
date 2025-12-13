from pathlib import Path

import ibis
import structlog
from ibis import BaseBackend

from causaganha.config import DB_PATH


logger = structlog.get_logger()

_connection = None


def get_connection(path: str = DB_PATH) -> BaseBackend:
    """Get or create DuckDB connection via Ibis.

    This is a singleton - returns the same connection instance.
    """
    global _connection

    if path == ":memory:":
        # For testing, return a new connection each time
        con = ibis.duckdb.connect()
        _initialize_schema(con)
        return con

    if _connection is None:
        if path != ":memory:" and not path.startswith(":memory:"):
            db_file = Path(path)
            db_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info("connecting_to_duckdb", path=str(path))
        _connection = ibis.duckdb.connect(path)

        # Initialize schema
        _initialize_schema(_connection)

    return _connection


def _initialize_schema(con: BaseBackend):
    """Create tables if they don't exist"""
    try:
        schema_file = Path(__file__).parent / "schema.sql"
        if schema_file.exists():
            schema_sql = schema_file.read_text()
            # Execute each statement
            for statement in schema_sql.split(";"):
                if statement.strip():
                    con.raw_sql(statement)
        else:
            logger.warning("schema_file_not_found", path=str(schema_file))

    except Exception as e:
        logger.error("schema_initialization_failed", error=str(e))
        raise
