
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from causaganha.cli import app


runner = CliRunner()

@pytest.fixture
def mock_db_connection() -> Generator[MagicMock, None, None]:
    with patch("causaganha.cli.get_connection") as mock_get:
        mock_con = MagicMock()
        mock_get.return_value = mock_con
        yield mock_con

@pytest.fixture
def mock_create_schema() -> Generator[MagicMock, None, None]:
    with patch("causaganha.cli.create_schema") as mock_create:
        yield mock_create

def test_db_init(mock_db_connection: MagicMock, mock_create_schema: MagicMock) -> None:
    result = runner.invoke(app, ["db", "init"])
    assert result.exit_code == 0
    assert "Initializing database schema..." in result.stdout
    assert "Schema created successfully." in result.stdout
    mock_create_schema.assert_called_once_with(mock_db_connection)

@pytest.mark.usefixtures("mock_db_connection")
def test_db_init_failure(mock_create_schema: MagicMock) -> None:
    mock_create_schema.side_effect = Exception("DB Error")
    result = runner.invoke(app, ["db", "init"])
    assert result.exit_code == 1
    assert "Initialization failed: DB Error" in result.stdout

def test_db_status(mock_db_connection: MagicMock) -> None:
    mock_db_connection.list_tables.return_value = ["table1", "table2"]
    result = runner.invoke(app, ["db", "status"])
    assert result.exit_code == 0
    assert "Connected to DuckDB. Found tables: ['table1', 'table2']" in result.stdout

@pytest.mark.usefixtures("mock_db_connection")
def test_db_unknown_action() -> None:
    result = runner.invoke(app, ["db", "unknown"])
    assert result.exit_code == 0  # Typer argument parsing passes, but our logic prints
    assert "Unknown action: unknown" in result.stdout
