"""DuckDB connection via Ibis."""

from pathlib import Path

import ibis
import structlog

from .schema import apply_schema


logger = structlog.get_logger()

_connection: ibis.BaseBackend | None = None


def get_connection(db_path: str = "data/causaganha.duckdb") -> ibis.BaseBackend:
    """Get or create DuckDB connection via Ibis.

    This is a singleton - returns the same connection instance.
    """
    global _connection

    if _connection is None:
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info("connecting_to_duckdb", path=str(db_file))
        _connection = ibis.duckdb.connect(str(db_file))

        # Initialize schema if needed
        _initialize_schema(_connection)

    return _connection


def _initialize_schema(con: ibis.BaseBackend) -> None:
    """Create tables if they don't exist."""
    apply_schema(con)
