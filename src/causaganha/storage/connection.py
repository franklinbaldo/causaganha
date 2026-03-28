"""DuckDB connection via Ibis."""

from pathlib import Path

import ibis
import structlog
from ibis.backends.duckdb import Backend


logger = structlog.get_logger()

_connections: dict[tuple[str, bool], Backend] = {}


def get_connection(
    db_path: str = "data/causaganha.duckdb",
    *,
    read_only: bool = False,
) -> Backend:
    """Get or create DuckDB connection via Ibis.

    This is a singleton per database path and mode - returns the same connection instance
    for the same (path, read_only) pair.
    """
    key = (db_path, read_only)

    if key not in _connections:
        if db_path != ":memory:":
            db_file = Path(db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            logger.info("connecting_to_duckdb", path=str(db_file), read_only=read_only)
            con = ibis.duckdb.connect(str(db_file), read_only=read_only)
        else:
            logger.info("connecting_to_duckdb_memory")
            con = ibis.duckdb.connect(db_path)

        # Initialize schema if needed (only for main DB or if requested?)
        # For now, initialize schema for all connections as it's harmless if empty
        # Note: If read_only is True, schema initialization might fail if writes are attempted.
        # But _initialize_schema checks existence first.
        if not read_only:
            _initialize_schema(con)
        _connections[key] = con

    return _connections[key]


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
