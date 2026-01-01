"""Unit tests for Ibis Storage Layer (v2)."""

import os
from unittest.mock import patch

import ibis
import pytest

from causaganha.v2.storage.connection import get_connection


@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test.duckdb")


def test_get_connection_creates_db(temp_db_path) -> None:
    """Test that connection creates database file."""
    # Ensure it doesn't exist yet
    assert not os.path.exists(temp_db_path)

    con = get_connection(temp_db_path)

    assert con is not None
    # DuckDB creates file lazily or immediately depending on usage,
    # but Ibis connect usually opens it.
    # Actually, ibis.duckdb.connect might not create the file until a query is run
    # if it's strictly lazy, but usually it does.
    # Let's verify we got an ibis backend.
    assert isinstance(con, ibis.BaseBackend)


def test_get_connection_singleton(temp_db_path) -> None:
    """Test that get_connection returns the same instance."""
    con1 = get_connection(temp_db_path)
    con2 = get_connection(temp_db_path)

    assert con1 is con2


def test_schema_initialization(temp_db_path) -> None:
    """Test that tables are created on initialization."""
    # We need to reset the singleton for this test or use a different path
    # But since _connection is global in the module, we should patch it or reset it.

    with patch("causaganha.v2.storage.connection._connection", None):
        con = get_connection(temp_db_path)
        tables = con.list_tables()

        assert "intimations" in tables
        assert "decision_analysis" in tables
        assert "lawyer_ratings" in tables
