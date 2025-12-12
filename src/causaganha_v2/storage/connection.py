import ibis
from ibis import BaseBackend
from causaganha_v2.config import DB_PATH

def get_connection(path: str = DB_PATH) -> BaseBackend:
    """
    Get a connection to the DuckDB database.

    Args:
        path: Path to the DuckDB database file. Defaults to DB_PATH from config.

    Returns:
        Ibis DuckDB connection backend.
    """
    if path == ":memory:":
        return ibis.duckdb.connect()

    return ibis.duckdb.connect(path)
