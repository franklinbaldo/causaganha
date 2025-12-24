
import pytest
from unittest.mock import AsyncMock, MagicMock
from causaganha.pipeline.archive import run_archive
from causaganha.storage.repository import IntimationRepository
from causaganha.services.document import DocumentService
from causaganha.services.archive import ArchiveService

@pytest.fixture
def mock_repository():
    return AsyncMock(spec=IntimationRepository)

@pytest.fixture
def mock_doc_service():
    service = AsyncMock(spec=DocumentService)
    service.download_pdf.return_value = b"fake pdf content"
    return service

@pytest.fixture
def mock_archive_service():
    service = AsyncMock(spec=ArchiveService)
    service.upload_file.return_value = "https://archive.org/details/some-item"
    service.generate_metadata.return_value = {}
    return service

@pytest.mark.asyncio
async def test_archive_uses_correct_court_in_id(
    mock_repository, mock_doc_service, mock_archive_service
):
    """Test that the archive pipeline uses the correct tribunal in the item ID."""

    # Setup data
    intimation = {
        "id": 12345,
        "sigla_tribunal": "TJMT",
        "link": "http://example.com/doc.pdf",
        "numero_processo": "123",
        "data_disponibilizacao": "2023-01-01"
    }

    mock_repository.get_unarchived_intimations.return_value = [intimation]

    # Run
    await run_archive(
        mock_repository,
        mock_doc_service,
        mock_archive_service,
        limit=1
    )

    # Verify
    mock_archive_service.upload_file.assert_called_once()
    args = mock_archive_service.upload_file.call_args
    # args[0] is file_path, args[1] is item_id
    item_id = args[0][1] # or args.args[1]

    # Should contain tjmt, not tjro
    assert "tjmt" in item_id
    assert "tjro" not in item_id
