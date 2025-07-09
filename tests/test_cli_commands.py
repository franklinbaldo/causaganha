from typer.testing import CliRunner
from unittest.mock import patch

from src.cli import app

runner = CliRunner()



def test_pipeline_run_command():
    with patch("src.cli.asyncio.run") as mock_run:
        mock_run.return_value = 0
        result = runner.invoke(app, ["pipeline", "run", "--date", "2025-01-01"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
