from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from causaganha.cli import app


runner = CliRunner()


@pytest.fixture
def mock_run_collection():
    with patch("causaganha.cli.run_collection", new_callable=AsyncMock) as mock:
        yield mock


def test_collect_uses_configured_courts_default(mock_run_collection) -> None:
    """Test that the collect command uses configured courts if no argument is provided."""
    with patch("causaganha.config.settings.COURTS", ["TJRO", "TJMT"]):
        # Invoke without --courts
        result = runner.invoke(app, ["collect"])

        assert result.exit_code == 0

        mock_run_collection.assert_called_once()
        # Check positional arguments
        # Signature: run_collection(repository, client, start_date, end_date, courts)
        args = mock_run_collection.call_args[0]
        assert len(args) >= 5
        assert args[4] == ["TJRO", "TJMT"]
