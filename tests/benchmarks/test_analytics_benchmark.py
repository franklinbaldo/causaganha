import time
from pathlib import Path

from src.database import DatabaseManager


def test_analytics_query(tmp_path: Path):
    """Benchmark aggregation query for analytics."""
    db_path = tmp_path / "analytics.duckdb"
    manager = DatabaseManager(db_path=db_path)
    conn = manager.connect()
    conn.execute("CREATE TABLE decisions (resultado TEXT)")
    conn.executemany(
        "INSERT INTO decisions VALUES (?)",
        [("procedente",)] * 500 + [("improcedente",)] * 500,
    )

    start = time.perf_counter()
    result = conn.execute(
        "SELECT resultado, COUNT(*) FROM decisions GROUP BY resultado"
    ).fetchall()
    duration = time.perf_counter() - start
    manager.close()

    assert len(result) == 2
    assert duration < 1.0
