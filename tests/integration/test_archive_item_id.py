import pytest
from unittest.mock import AsyncMock, MagicMock
from causaganha.pipeline.archive import _process_intimation

@pytest.mark.asyncio
async def test_process_intimation_uses_dynamic_tribunal_in_item_id() -> None:
    """Test that _process_intimation constructs item_id using sigla_tribunal."""

    mock_doc_service = MagicMock()
    mock_doc_service.download_pdf = AsyncMock(return_value=b"fake content")

    mock_archive_service = MagicMock()
    mock_archive_service.upload_file = AsyncMock(return_value="http://ia.url")
    mock_archive_service.generate_metadata.return_value = {}

    mock_repo = AsyncMock()

    # Intimation with TJMT
    intimation = {
        "id": "123",
        "link": "http://doc.url",
        "sigla_tribunal": "TJMT"
    }

    await _process_intimation(
        intimation=intimation,
        doc_service=mock_doc_service,
        archive_service=mock_archive_service,
        repository=mock_repo,
        dry_run=False
    )

    # Verify upload_file called with item_id containing 'tjmt'
    mock_archive_service.upload_file.assert_called_once()
    item_id = mock_archive_service.upload_file.call_args[0][1]
    assert item_id == "causaganha-tjmt-123"

    # Reset mocks
    mock_archive_service.upload_file.reset_mock()

    # Intimation without sigla_tribunal (legacy case)
    intimation_legacy = {
        "id": "456",
        "link": "http://doc.url"
        # Missing sigla_tribunal
    }

    await _process_intimation(
        intimation=intimation_legacy,
        doc_service=mock_doc_service,
        archive_service=mock_archive_service,
        repository=mock_repo,
        dry_run=False
    )

    # Verify upload_file called with item_id containing default 'tjro'
    mock_archive_service.upload_file.assert_called_once()
    item_id = mock_archive_service.upload_file.call_args[0][1]
    assert item_id == "causaganha-tjro-456"
