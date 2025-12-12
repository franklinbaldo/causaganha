"""DuckDB connection via Ibis"""

import ibis
from pathlib import Path
import structlog

logger = structlog.get_logger()

_connection = None

def get_connection(db_path: str = "data/causaganha.duckdb") -> ibis.BaseBackend:
    """
    Get or create DuckDB connection via Ibis

    This is a singleton - returns the same connection instance
    """
    global _connection

    if _connection is None:
        if db_path != ":memory:":
            db_file = Path(db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            logger.info("connecting_to_duckdb", path=str(db_file))

        _connection = ibis.duckdb.connect(db_path)

        # Initialize schema if needed
        _initialize_schema(_connection)

    return _connection

def _initialize_schema(con: ibis.BaseBackend):
    """Create tables if they don't exist"""

    tables = con.list_tables()

    if 'intimations' not in tables:
        logger.info("creating_schema")

        # Read schema from SQL file
        schema_file = Path(__file__).parent / "schema.sql"
        if schema_file.exists():
            schema_sql = schema_file.read_text()
            # Execute each statement
            for statement in schema_sql.split(';'):
                if statement.strip():
                    try:
                        con.raw_sql(statement)
                    except Exception as e:
                        # Some statements might fail if table exists but list_tables missed it?
                        # Or syntax error.
                        logger.warning("schema_execution_error", statement=statement[:50], error=str(e))
                        raise e
        else:
            logger.warning("schema_file_not_found",
                          path=str(schema_file))
