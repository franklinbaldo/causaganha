
import json
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
def test_db_init_failure_shows_suggestions(mock_create_schema: MagicMock) -> None:
    """Tests if actionable suggestions are displayed on failure."""
    mock_create_schema.side_effect = OSError("Permission denied")
    result = runner.invoke(app, ["db", "init"])
    assert result.exit_code == 1
    assert "Actionable Suggestions" in result.stdout
    assert "Permission denied" in result.stdout


@pytest.mark.usefixtures("mock_db_connection")
def test_error_message_is_colored(mock_create_schema: MagicMock) -> None:
    """Tests if the error message is colored red."""
    mock_create_schema.side_effect = Exception("DB Error")
    # The runner strips ANSI codes by default, so we can't directly check color.
    # Instead, we rely on the fact that _handle_error uses typer.secho
    # and test the content, assuming typer handles the coloring.
    # For a more robust check, one might need to capture raw stdout.
    result = runner.invoke(app, ["db", "init"])
    assert result.exit_code == 1
    assert "❌ Initialization failed" in result.stdout

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
def test_collect_failure(mock_run_collection: MagicMock, mock_pje_client: MagicMock) -> None:
    """Tests the error handler for the collect command."""
    mock_run_collection.side_effect = RuntimeError("API unavailable")
    result = runner.invoke(app, ["collect", "--courts", "TJSP"])
    assert result.exit_code == 1
    assert "❌ Collection failed" in result.stdout
    assert "API unavailable" in result.stdout
    mock_pje_client.close.assert_called_once()

@pytest.mark.usefixtures("mock_db_connection", "mock_create_schema", "mock_repository")
def test_analyze(mock_run_analysis: MagicMock) -> None:
    with patch("causaganha.cli.DecisionAnalyzer"), patch("causaganha.cli.DocumentService"):
        result = runner.invoke(app, ["analyze", "--limit", "5"])
        assert result.exit_code == 0
        mock_run_analysis.assert_called_once()
        _args, kwargs = mock_run_analysis.call_args
        assert kwargs["limit"] == 5


@pytest.mark.usefixtures("mock_db_connection", "mock_create_schema", "mock_repository")
def test_analyze_failure(mock_run_analysis: MagicMock) -> None:
    """Tests the error handler for the analyze command."""
    mock_run_analysis.side_effect = ValueError("Invalid document format")
    with patch("causaganha.cli.DecisionAnalyzer"), patch("causaganha.cli.DocumentService"):
        result = runner.invoke(app, ["analyze"])
        assert result.exit_code == 1
        assert "❌ Analysis failed" in result.stdout
        assert "Invalid document format" in result.stdout


@pytest.mark.usefixtures("mock_db_connection", "mock_create_schema", "mock_repository")
def test_archive(mock_run_archive: MagicMock) -> None:
    with patch("causaganha.cli.create_archive_service"):
        with patch("causaganha.cli.DocumentService"):
            result = runner.invoke(app, ["archive", "--limit", "3", "--dry-run"])
            assert result.exit_code == 0
            mock_run_archive.assert_called_once()
            _args, kwargs = mock_run_archive.call_args
            assert kwargs["limit"] == 3
            assert kwargs["dry_run"] is True


@pytest.mark.usefixtures("mock_db_connection", "mock_create_schema", "mock_repository")
def test_archive_failure(mock_run_archive: MagicMock) -> None:
    """Tests the error handler for the archive command."""
    mock_run_archive.side_effect = ConnectionError("Upload failed")
    with patch("causaganha.cli.create_archive_service"):
        with patch("causaganha.cli.DocumentService"):
            result = runner.invoke(app, ["archive"])
            assert result.exit_code == 1
            assert "❌ Archive failed" in result.stdout
            assert "Upload failed" in result.stdout


@pytest.mark.usefixtures("mock_db_connection", "mock_create_schema", "mock_repository")
def test_score(mock_run_scoring: MagicMock) -> None:
    result = runner.invoke(app, ["score", "--limit", "50"])
    assert result.exit_code == 0
    mock_run_scoring.assert_called_once()
    # Check arguments
    _args, kwargs = mock_run_scoring.call_args
    assert kwargs["limit"] == 50


@pytest.mark.usefixtures("mock_db_connection", "mock_create_schema", "mock_repository")
def test_score_failure(mock_run_scoring: MagicMock) -> None:
    """Tests the error handler for the score command."""
    mock_run_scoring.side_effect = KeyError("Rating not found")
    result = runner.invoke(app, ["score"])
    assert result.exit_code == 1
    assert "❌ Scoring failed" in result.stdout
    assert "Rating not found" in result.stdout


@pytest.mark.usefixtures("mock_db_connection", "mock_create_schema", "mock_repository")
def test_pipeline(
    mock_run_collection: MagicMock,
    mock_run_archive: MagicMock,
    mock_run_analysis: MagicMock,
    mock_run_scoring: MagicMock,
    mock_pje_client: MagicMock,
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

@pytest.mark.usefixtures("mock_db_connection", "mock_create_schema", "mock_repository")
def test_pipeline_skips(
    mock_run_collection: MagicMock,
    mock_run_archive: MagicMock,
    mock_run_analysis: MagicMock,
    mock_run_scoring: MagicMock,
    mock_pje_client: MagicMock,
) -> None:
    # We need to mock services instantiated in pipeline
    with patch("causaganha.cli.create_archive_service"), \
         patch("causaganha.cli.DocumentService"), \
         patch("causaganha.cli.DecisionAnalyzer"):

        # Skip all steps
        result = runner.invoke(app, [
            "pipeline",
            "--skip-collect",
            "--skip-archive",
            "--skip-analyze",
            "--skip-score",
        ])

        assert result.exit_code == 0
        assert "Pipeline complete!" in result.stdout
        assert "Skipping collection" in result.stdout
        assert "Skipping archive" in result.stdout
        assert "Skipping analysis" in result.stdout
        assert "Skipping scoring" in result.stdout

        mock_run_collection.assert_not_called()
        mock_run_archive.assert_not_called()
        mock_run_analysis.assert_not_called()
        mock_run_scoring.assert_not_called()
        mock_pje_client.close.assert_called_once()


@pytest.fixture
def mock_rich_progress() -> Generator[MagicMock, None, None]:
    """Fixture to mock rich.progress.Progress."""
    # We patch it where it's used, which will be in the cli module.
    # This will fail with an AttributeError until the import is added.
    with patch("causaganha.cli.Progress", create=True) as mock_progress:
        yield mock_progress


@pytest.mark.usefixtures("mock_db_connection", "mock_create_schema", "mock_repository")
def test_collect_shows_progress(
    mock_run_collection: MagicMock,
    mock_pje_client: MagicMock,
    mock_rich_progress: MagicMock,
) -> None:
    """Tests that the collect command shows a progress indicator."""
    result = runner.invoke(app, ["collect"])
    assert result.exit_code == 0
    mock_run_collection.assert_called_once()
    mock_pje_client.close.assert_called_once()
    mock_rich_progress.assert_called_once()


@pytest.mark.usefixtures("mock_db_connection", "mock_create_schema", "mock_repository")
def test_analyze_shows_progress(
    mock_run_analysis: MagicMock, mock_rich_progress: MagicMock,
) -> None:
    """Tests that the analyze command shows a progress indicator."""
    with patch("causaganha.cli.DecisionAnalyzer"), patch(
        "causaganha.cli.DocumentService",
    ):
        result = runner.invoke(app, ["analyze"])
        assert result.exit_code == 0
        mock_run_analysis.assert_called_once()
        mock_rich_progress.assert_called_once()


@pytest.mark.usefixtures("mock_db_connection", "mock_create_schema", "mock_repository")
def test_archive_shows_progress(
    mock_run_archive: MagicMock, mock_rich_progress: MagicMock,
) -> None:
    """Tests that the archive command shows a progress indicator."""
    with patch("causaganha.cli.create_archive_service"), patch(
        "causaganha.cli.DocumentService",
    ):
        result = runner.invoke(app, ["archive"])
        assert result.exit_code == 0
        mock_run_archive.assert_called_once()
        mock_rich_progress.assert_called_once()


import structlog


@patch("causaganha.cli._get_repository")
def test_manifest_export(mock_get_repo: MagicMock) -> None:
    """Test the manifest export command."""
    # Reconfigure structlog to suppress output, effectively silencing it
    structlog.configure(
        processors=[],
        logger_factory=structlog.stdlib.LoggerFactory(),  # Use standard logging which we can capture/silence
    )
    # Further ensure logs don't hit stdout during the test by disabling handlers if possible,
    # or rely on CliRunner capturing stdout. The issue is likely mixed content.
    # A cleaner way: Mock structlog.get_logger in the cli module.

    with patch("causaganha.cli.logger", new=MagicMock()):
        # Mock the repository and its method
        mock_repo = MagicMock()

        async def get_all_intimations(limit: int) -> list[dict]:
            return [
                {
                    "id": 1,
                    "numero_processo": "123",
                    "sigla_tribunal": "TJRO",
                    "data_disponibilizacao": "2024-01-01",
                    "link": "http://example.com/pdf",
                    "needs_download": True,
                    "ia_url": None,
                },
            ]

        mock_repo.get_all_intimations = AsyncMock(side_effect=get_all_intimations)
        mock_get_repo.return_value = mock_repo

        runner = CliRunner()
        result = runner.invoke(app, ["manifest", "export", "--limit", "1"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)

        assert len(output) == 1
        assert output[0]["intimation_id"] == 1
        assert output[0]["process_number"] == "123"
        assert output[0]["tribunal"] == "TJRO"
        assert output[0]["decision_date"] == "2024-01-01"
        assert output[0]["needs_download"] is True
