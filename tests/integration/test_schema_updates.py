import pytest
import ibis
from causaganha.storage.connection import get_connection
from causaganha.storage.migrations import run_migrations


def test_schema_migrations_and_constraints():
    # 1. Setup in-memory DB
    con = get_connection(":memory:")

    # 2. Run migrations
    applied = run_migrations(con)
    assert "create_git_refs" in applied
    assert "create_git_commits" in applied
    assert "create_asset_cache" in applied
    assert "create_messages" in applied

    # 3. Verify tables exist
    tables = con.list_tables()
    assert "git_refs" in tables
    assert "git_commits" in tables
    assert "asset_cache" in tables
    assert "messages" in tables

    # 4. Verify messages constraint
    # Valid insert
    con.raw_sql("""
        INSERT INTO messages (role, content, media_type)
        VALUES ('user', 'hello', 'text/plain')
    """)

    # Invalid insert (should fail CHECK constraint)
    with pytest.raises(Exception) as excinfo:
        con.raw_sql("""
            INSERT INTO messages (role, content, media_type)
            VALUES ('user', 'hello', 'application/x-invalid')
        """)
    assert "Constraint Error" in str(excinfo.value) or "CHECK constraint" in str(excinfo.value)

    # 5. Verify Asset Cache Index
    # DuckDB system table for indexes
    indexes = con.raw_sql("SELECT index_name FROM duckdb_indexes()").fetchall()
    index_names = [row[0] for row in indexes]
    assert "idx_asset_cache_expires" in index_names

    print("Schema verification passed!")


if __name__ == "__main__":
    test_schema_migrations_and_constraints()
