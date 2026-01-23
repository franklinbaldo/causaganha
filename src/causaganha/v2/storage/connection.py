"""DuckDB connection via Ibis."""

import ibis
from ibis import _
from pathlib import Path
import structlog

logger = structlog.get_logger()

_connection = None

def get_connection(db_path: str = "data/causaganha.duckdb") -> ibis.backends.duckdb.Backend:
    """
    Get or create DuckDB connection via Ibis.

    This is a singleton - returns the same connection instance.
    """
    global _connection

    if _connection is None:
        if db_path == ":memory:":
             _connection = ibis.duckdb.connect(":memory:")
        else:
            db_file = Path(db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            logger.info("connecting_to_duckdb", path=str(db_file))
            _connection = ibis.duckdb.connect(str(db_file))

        # Initialize schema if needed
        _initialize_schema(_connection)

    return _connection

def _initialize_schema(con: ibis.backends.duckdb.Backend):
    """Create tables if they don't exist."""

    tables = con.list_tables()

    if 'intimations' not in tables:
        logger.info("creating_schema")

        # Read schema from SQL file
        schema_file = Path(__file__).parent / "schema.sql"
        if schema_file.exists():
            schema_sql = schema_file.read_text()
            # Execute each statement
            # Split by ';' but be careful about semicolons inside strings.
            # For simplicity, assuming standard SQL file structure.
            for statement in schema_sql.split(';'):
                if statement.strip():
                    try:
                        con.raw_sql(statement)
                    except Exception as e:
                        logger.error("schema_initialization_error", error=str(e), statement=statement[:100])
                        raise
        else:
            logger.warning("schema_file_not_found",
                          path=str(schema_file))
