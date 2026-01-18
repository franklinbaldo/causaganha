from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from causaganha.cli import app
from causaganha.v2.api.client import Intimation
from causaganha.v2.storage.queries import store_intimations

runner = CliRunner()

@pytest.fixture
def mock_dependencies():
    with patch("causaganha.cli.create_archive_service") as mock_archive_service, \
         patch("causaganha.cli.DocumentService") as mock_doc_service, \
         patch("causaganha.v2.pipeline.archive.PreservationService") as mock_preservation:

        # Setup mocks
        mock_doc_instance = mock_doc_service.return_value
        mock_archive_instance = mock_archive_service.return_value
        mock_pres_instance = mock_preservation.return_value

        # Mock preserve_document to respect dry_run
        async def _preserve(url, item_id, metadata, dry_run=False):
            if dry_run:
                return None
            return "https://archive.org/123"

        mock_pres_instance.preserve_document = AsyncMock(side_effect=_preserve)

        yield mock_doc_instance, mock_archive_instance, mock_pres_instance

def test_archive_command(mock_dependencies, db_connection):
    """Test the archive command via CLI."""
    with patch("causaganha.v2.pipeline.archive.get_connection", return_value=db_connection):
        # Insert test data
        intimation = Intimation(
            id=123,
            numero_processo="123-45.2024.8.22.0001",
            link="http://pdf",
            data_disponibilizacao="2024-01-01",
            siglaTribunal="TJRO",
            texto="Test intimation"
        )
        store_intimations(db_connection, [intimation])

        result = runner.invoke(app, ["archive", "--limit", "1"])

        assert result.exit_code == 0
        # Check for structured logs in output
        assert "archive_start" in result.stdout
        assert "archived_success" in result.stdout

        # Verify
        res = db_connection.table("intimations").execute()
        assert res["ia_url"].iloc[0] == "https://archive.org/123"

def test_archive_command_dry_run(mock_dependencies, db_connection):
    """Test dry run."""
    with patch("causaganha.v2.pipeline.archive.get_connection", return_value=db_connection):
        intimation = Intimation(
            id=124,
            numero_processo="124-45.2024.8.22.0001",
            link="http://pdf",
            data_disponibilizacao="2024-01-01",
            siglaTribunal="TJRO",
            texto="Test intimation"
        )
        store_intimations(db_connection, [intimation])

        result = runner.invoke(app, ["archive", "--limit", "1", "--dry-run"])

        assert result.exit_code == 0

        assert "dry_run_archived" in result.stdout or "dry_run=True" in result.stdout

        res = db_connection.table("intimations").execute()
        # Should be None
        assert res[res["id"] == 124]["ia_url"].isnull().all()
