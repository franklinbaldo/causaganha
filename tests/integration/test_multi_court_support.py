from unittest.mock import AsyncMock, Mock, patch, MagicMock
import pytest
from causaganha.pipeline.collect import run_collection
from causaganha.pipeline.archive import run_archive

@pytest.mark.asyncio
async def test_collect_defaults_to_settings_courts():
    """Verify that run_collection uses settings.COURTS if courts arg is None."""
    repository = Mock()
    repository.store_intimations = AsyncMock()
    client = AsyncMock()

    # We mock settings.COURTS to include multiple courts
    # We must patch where settings is used, which will be causaganha.pipeline.collect.settings
    # But since it's not imported yet, this test will fail or error.
    # We'll patch 'causaganha.config.settings' and hope the implementation uses it.

    with patch("causaganha.pipeline.collect.settings", create=True) as mock_settings:
        mock_settings.COURTS = ["TJMT", "TJRO"]

        await run_collection(repository, client, "2023-01-01", "2023-01-02", courts=None)

        # Verify get_intimations_by_court was called for both
        calls = client.get_intimations_by_court.call_args_list
        tribunals = [call.kwargs['sigla_tribunal'] for call in calls]

        assert "TJMT" in tribunals
        assert "TJRO" in tribunals
        assert len(tribunals) == 2

@pytest.mark.asyncio
async def test_archive_uses_correct_tribunal_in_item_id():
    """Verify that run_archive generates item_id based on intimation tribunal."""
    repository = Mock()
    doc_service = Mock()
    archive_service = Mock()

    # Mock data with specific tribunal
    intimation = {
        "id": 123,
        "sigla_tribunal": "TJMT",
        "link": "http://example.com/doc.pdf",
        "numero_processo": "12345",
        "data_disponibilizacao": "2023-01-01"
    }

    # Setup repository to return this intimation
    repository.get_unarchived_intimations = AsyncMock(return_value=[intimation])
    repository.mark_as_archived = AsyncMock()

    # Setup services
    doc_service.download_pdf = AsyncMock(return_value=b"pdf content")
    archive_service.upload_file = AsyncMock(return_value="http://archive.org/details/foo")
    archive_service.generate_metadata = Mock(return_value={})

    # Run archive
    await run_archive(repository, doc_service, archive_service, limit=1, dry_run=False)

    # Verify upload_file was called with correct item_id
    # Signature: upload_file(file_path, item_id, metadata)
    assert archive_service.upload_file.called
    call_args = archive_service.upload_file.call_args
    _, item_id, _ = call_args[0]

    # Should contain tribunal lowercased
    assert "tjmt" in item_id
    assert "tjro" not in item_id
