import time
from pathlib import Path

import duckdb


def test_duckdb_join_query(tmp_path: Path):
    """Benchmark a join query on two large tables."""
    db_file = tmp_path / "join_bench.duckdb"
    conn = duckdb.connect(str(db_file))
    conn.execute(
        "CREATE TABLE a AS SELECT i AS id, 'text' || i::TEXT AS data FROM range(0, 100000) t(i)"
    )
    conn.execute(
        "CREATE TABLE b AS SELECT i AS id, i * 2 AS value FROM range(0, 100000) t(i)"
    )

    start = time.perf_counter()
    result = conn.execute(
        "SELECT COUNT(*) FROM a JOIN b USING (id) WHERE value % 2 = 0"
    ).fetchone()
    duration = time.perf_counter() - start
    conn.close()

    assert result[0] == 100000
    assert duration < 1.0
