import time
from pathlib import Path

from src.database import DatabaseManager


def test_database_connect_insert(tmp_path: Path):
    """Benchmark basic database connection and insert operations."""
    db_path = tmp_path / "bench.duckdb"
    start = time.perf_counter()
    manager = DatabaseManager(db_path=db_path)
    conn = manager.connect()
    conn.execute("CREATE TABLE bench (id INTEGER)")
    conn.execute("INSERT INTO bench VALUES (1)")
    conn.execute("SELECT COUNT(*) FROM bench").fetchone()
    manager.close()
    duration = time.perf_counter() - start
    # Expect basic operations to finish quickly
    assert duration < 1.0
