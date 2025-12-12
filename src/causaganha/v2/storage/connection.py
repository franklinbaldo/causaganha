"""Database connection management."""
import asyncio
from functools import lru_cache

import ibis
from ibis import BaseBackend

from causaganha.config import DB_PATH


@lru_cache(maxsize=1)
def _get_persistent_connection(path: str) -> BaseBackend:
    """Internal helper to cache persistent connections."""
    return ibis.duckdb.connect(path)


async def get_connection(path: str = DB_PATH) -> BaseBackend:
    """Get a connection to the DuckDB database.

    Args:
        path: Path to the DuckDB database file. Defaults to DB_PATH from config.

    Returns:
        Ibis DuckDB connection backend.
    """
    if path == ":memory:":
        return await asyncio.to_thread(ibis.duckdb.connect)

    return await asyncio.to_thread(_get_persistent_connection, path)
