import sys
from pathlib import Path

import duckdb


# Ensure scripts is in pythonpath
sys.path.append(str(Path(__file__).parent.parent.parent))

from causaganha.infrastructure.storage.connection import get_connection
from causaganha.infrastructure.storage.schema import create_schema
from scripts.migrate_v1_to_v2 import migrate_ratings, parse_v1_lawyer_id


def test_parse_lawyer_id() -> None:
    name, oab, state = parse_v1_lawyer_id("FRANKLIN SILVEIRA BALDO (OAB/RO 5733)")
    assert name == "FRANKLIN SILVEIRA BALDO"
    assert oab == "5733"
    assert state == "RO"

    name, oab, state = parse_v1_lawyer_id("JOSE DA SILVA (OAB/SP 12345A)")
    assert name == "JOSE DA SILVA"
    assert oab == "12345A"
    assert state == "SP"

    name, oab, state = parse_v1_lawyer_id("INVALID ID")
    assert name is None


def test_migrate_ratings(tmp_path: Path) -> None:
    # Setup V1 DB
    v1_db_path = tmp_path / "v1_test.duckdb"
    v1_con = duckdb.connect(str(v1_db_path))
    v1_con.execute(
        "CREATE TABLE ratings (advogado_id VARCHAR, mu DOUBLE, sigma DOUBLE, total_partidas INTEGER, created_at TIMESTAMP, updated_at TIMESTAMP)"
    )

    # Insert sample V1 data
    # Include NULL values to test robustness
    v1_con.execute("""
        INSERT INTO ratings VALUES
        ('LAWYER ONE (OAB/RO 1111)', 28.0, 7.0, 10, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('LAWYER TWO (OAB/SP 2222)', 22.0, 8.0, 5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('LAWYER THREE (OAB/MG 3333)', NULL, 8.333, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('BAD ID FORMAT', 25.0, 8.333, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """)
    v1_con.close()

    # Setup V2 DB
    v2_db_path = tmp_path / "v2_test.duckdb"
    v2_con = get_connection(str(v2_db_path))
    # Ensure schema exists
    create_schema(v2_con)

    # Run migration
    migrate_ratings(str(v1_db_path), v2_con)

    # Verify V2 data
    t = v2_con.table("lawyer_ratings")
    ratings = t.execute()

    assert len(ratings) == 3  # Should migrate 3 valid IDs, skipping BAD ID

    l1 = ratings[ratings["oab_number"] == "1111"].iloc[0]
    assert l1["lawyer_name"] == "LAWYER ONE"
    assert l1["oab_state"] == "RO"
    assert l1["mu"] == 28.0
    assert l1["total_cases"] == 10

    l2 = ratings[ratings["oab_number"] == "2222"].iloc[0]
    assert l2["lawyer_name"] == "LAWYER TWO"
    assert l2["oab_state"] == "SP"
    assert l2["mu"] == 22.0

    l3 = ratings[ratings["oab_number"] == "3333"].iloc[0]
    assert l3["lawyer_name"] == "LAWYER THREE"
    # DuckDB/Pandas handles NULL as NaN for floats
    import math

    assert math.isnan(l3["mu"])
