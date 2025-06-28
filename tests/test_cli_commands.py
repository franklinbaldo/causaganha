from typer.testing import CliRunner
from unittest.mock import patch

from src.cli import app

runner = CliRunner()


def test_db_sync_command():
    with patch("ia_database_sync.IADatabaseSync") as MockSync:
        instance = MockSync.return_value
        instance.smart_sync.return_value = "already_synced"
        result = runner.invoke(app, ["db", "sync"])
        assert result.exit_code == 0
        assert "already_synced" in result.stdout
        instance.smart_sync.assert_called_once()


def test_pipeline_run_command():
    with patch("src.cli.asyncio.run") as mock_run:
        mock_run.return_value = 0
        result = runner.invoke(app, ["pipeline", "run", "--date", "2025-01-01"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
