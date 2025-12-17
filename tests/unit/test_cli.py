
import asyncio
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

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

@pytest.fixture
def mock_repository() -> Generator[MagicMock, None, None]:
    with patch("causaganha.cli.IntimationRepository") as mock_repo:
        yield mock_repo

@pytest.fixture
def mock_run_collection() -> Generator[MagicMock, None, None]:
    with patch("causaganha.cli.run_collection", new_callable=AsyncMock) as mock_run:
        yield mock_run

@pytest.fixture
def mock_run_analysis() -> Generator[MagicMock, None, None]:
    with patch("causaganha.cli.run_analysis", new_callable=AsyncMock) as mock_run:
        yield mock_run

@pytest.fixture
def mock_run_archive() -> Generator[MagicMock, None, None]:
    with patch("causaganha.cli.run_archive", new_callable=AsyncMock) as mock_run:
        yield mock_run

@pytest.fixture
def mock_run_scoring() -> Generator[MagicMock, None, None]:
    with patch("causaganha.cli.run_scoring", new_callable=AsyncMock) as mock_run:
        yield mock_run

@pytest.fixture
def mock_pje_client() -> Generator[MagicMock, None, None]:
    with patch("causaganha.cli.PJeAPIClient") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.close = AsyncMock()
        mock_cls.return_value = mock_instance
        yield mock_instance

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

@pytest.mark.usefixtures("mock_db_connection", "mock_create_schema", "mock_repository")
def test_collect(mock_run_collection: MagicMock, mock_pje_client: MagicMock) -> None:
    result = runner.invoke(app, ["collect", "--courts", "TJSP"])
    assert result.exit_code == 0
    mock_run_collection.assert_called_once()
    # Check that PJeAPIClient was used and closed
    mock_pje_client.close.assert_called_once()

@pytest.mark.usefixtures("mock_db_connection", "mock_create_schema", "mock_repository")
def test_analyze(mock_run_analysis: MagicMock) -> None:
    with patch("causaganha.cli.DecisionAnalyzer") as mock_analyzer:
        with patch("causaganha.cli.DocumentService"):
            result = runner.invoke(app, ["analyze", "--limit", "5"])
            assert result.exit_code == 0
            mock_run_analysis.assert_called_once()
            args, kwargs = mock_run_analysis.call_args
            assert kwargs["limit"] == 5

@pytest.mark.usefixtures("mock_db_connection", "mock_create_schema", "mock_repository")
def test_archive(mock_run_archive: MagicMock) -> None:
    with patch("causaganha.cli.create_archive_service"):
        with patch("causaganha.cli.DocumentService"):
            result = runner.invoke(app, ["archive", "--limit", "3", "--dry-run"])
            assert result.exit_code == 0
            mock_run_archive.assert_called_once()
            args, kwargs = mock_run_archive.call_args
            assert kwargs["limit"] == 3
            assert kwargs["dry_run"] is True

def test_score(mock_run_scoring: MagicMock) -> None:
    result = runner.invoke(app, ["score", "--limit", "50"])
    assert result.exit_code == 0
    mock_run_scoring.assert_called_once()
    # Check arguments
    args, kwargs = mock_run_scoring.call_args
    assert kwargs["limit"] == 50

@pytest.mark.usefixtures("mock_db_connection", "mock_create_schema", "mock_repository")
def test_pipeline(
    mock_run_collection: MagicMock,
    mock_run_archive: MagicMock,
    mock_run_analysis: MagicMock,
    mock_run_scoring: MagicMock,
    mock_pje_client: MagicMock
) -> None:
    # We need to mock services instantiated in pipeline
    with patch("causaganha.cli.create_archive_service"), \
         patch("causaganha.cli.DocumentService"), \
         patch("causaganha.cli.DecisionAnalyzer"):

        result = runner.invoke(app, ["pipeline", "--score-limit", "10"])

        assert result.exit_code == 0
        assert "Pipeline complete!" in result.stdout

        mock_run_collection.assert_called_once()
        mock_run_archive.assert_called_once()
        mock_run_analysis.assert_called_once()
        mock_run_scoring.assert_called_once()
        mock_pje_client.close.assert_called_once()
