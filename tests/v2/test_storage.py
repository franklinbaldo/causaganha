"""
TDD for Ibis Storage Layer
"""

import pytest
import ibis
from pathlib import Path
from unittest.mock import patch, MagicMock
from causaganha.v2.storage.connection import get_connection

def test_get_connection_creates_duckdb_file(tmp_path):
    """Test that connection creates the database file"""
    db_path = tmp_path / "test.duckdb"

    # Reset singleton if exists (though we can't easily access the module level variable to reset it perfectly without reloading,
    # but we can pass the path to get_connection)

    # Since get_connection uses a global variable, we need to be careful.
    # We will mock ibis.duckdb.connect to verify it's called with the correct path

    with patch('causaganha.v2.storage.connection.ibis.duckdb.connect') as mock_connect:
        with patch('causaganha.v2.storage.connection._connection', None): # Reset singleton for this test
            get_connection(str(db_path))

            mock_connect.assert_called_once_with(str(db_path))

def test_schema_initialization(tmp_path):
    """Test that schema is initialized on first connection"""
    db_path = tmp_path / "test_schema.duckdb"

    # Create a real DuckDB connection to verify table creation
    con = ibis.duckdb.connect(str(db_path))

    # We need to simulate get_connection behavior
    # For this test, we'll actually use the real get_connection with a fresh path
    # and rely on it creating the tables.

    # But first, we need the schema.sql file to exist.
    # The implementation will look for schema.sql in the same dir as connection.py
    # So we should probably implement connection.py and schema.sql first or mock the reading.

    # Let's mock the schema reading for now to be pure unit test

    with patch('causaganha.v2.storage.connection.ibis.duckdb.connect') as mock_connect:
        mock_con = MagicMock()
        mock_connect.return_value = mock_con
        mock_con.list_tables.return_value = [] # No tables exist

        with patch('causaganha.v2.storage.connection.Path') as mock_path:
            # Mock reading schema.sql
            mock_file = MagicMock()
            mock_path.return_value.parent.__truediv__.return_value = mock_file
            mock_file.exists.return_value = True
            mock_file.read_text.return_value = "CREATE TABLE test (id INT);"

            with patch('causaganha.v2.storage.connection._connection', None):
                get_connection("dummy.db")

                # Should have executed the SQL
                mock_con.raw_sql.assert_called()
