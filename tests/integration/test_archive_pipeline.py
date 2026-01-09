"""Tests for archive pipeline."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from causaganha.pipeline.archive import _process_intimation, run_archive
from causaganha.services.archive import InternetArchiveService
from causaganha.services.document import DocumentService
from causaganha.storage.repositories.intimation import IntimationRepository


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    repo = MagicMock(spec=IntimationRepository)
    repo.get_unarchived_intimations = AsyncMock(return_value=[
        {
            "id": "test-id-1",
            "url_documento": "https://example.com/doc1.pdf",
            "link": "https://example.com/doc1.pdf",
        },
        {
            "id": "test-id-2",
            "url_documento": "https://example.com/doc2.pdf",
            "link": "https://example.com/doc2.pdf",
        },
    ])
    repo.mark_as_archived = AsyncMock()
    return repo


@pytest.fixture
def mock_doc_service():
    """Create a mock document service."""
    service = MagicMock(spec=DocumentService)
    service.download_pdf = AsyncMock(return_value=b"fake pdf content")
    return service


@pytest.fixture
def mock_ia_service():
    """Create a mock IA service."""
    service = MagicMock(spec=InternetArchiveService)
    service.upload_file = AsyncMock(return_value="https://archive.org/details/test-item")
    return service


@pytest.mark.asyncio
async def test_run_archive_success(mock_repository, mock_doc_service, mock_ia_service) -> None:
    """Test successful archive pipeline run."""
    await run_archive(
        mock_repository,
        mock_doc_service,
        mock_ia_service,
        limit=2,
        dry_run=False,
    )

    # Verify repository was called
    mock_repository.get_unarchived_intimations.assert_called_once_with(limit=2)


@pytest.mark.asyncio
async def test_run_archive_no_intimations(mock_repository, mock_doc_service, mock_ia_service) -> None:
    """Test archive pipeline with no intimations."""
    mock_repository.get_unarchived_intimations.return_value = []

    await run_archive(
        mock_repository,
        mock_doc_service,
        mock_ia_service,
        limit=10,
        dry_run=False,
    )

    # Verify no downloads occurred
    mock_doc_service.download_pdf.assert_not_called()


@pytest.mark.asyncio
async def test_run_archive_dry_run(mock_repository, mock_doc_service, mock_ia_service, tmp_path) -> None:
    """Test archive pipeline in dry run mode."""
    # Set up temp directory
    # Patch PreservationService to avoid actual file system ops if needed, or check logs

    # We patch Path in preservation service because pipeline imports it? No, pipeline imports PreservationService.
    # PreservationService uses Path.
    # If we patch 'causaganha.services.preservation.Path', it should work for the service.

    with patch("causaganha.services.preservation.Path") as mock_path:
        # Mock Path behaviors
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        # Mocking temp_dir creation
        mock_path.return_value.__truediv__.return_value = mock_path_instance
        mock_path_instance.exists.return_value = False

        await run_archive(
            mock_repository,
            mock_doc_service,
            mock_ia_service,
            limit=2,
            dry_run=True,
        )

        # In dry run, files should not be uploaded
        mock_ia_service.upload_file.assert_not_called()


@pytest.mark.asyncio
async def test_process_intimation_no_url(mock_doc_service, mock_ia_service, mock_repository) -> None:
    """Test processing intimation without document URL."""
    intimation = {"id": "test-id", "url_documento": None}

    await _process_intimation(
        intimation,
        mock_doc_service,
        mock_ia_service,
        mock_repository,
        False,
    )

    # Should not attempt download
    mock_doc_service.download_pdf.assert_not_called()


@pytest.mark.asyncio
async def test_process_intimation_download_failure(mock_doc_service, mock_ia_service, mock_repository) -> None:
    """Test processing intimation with download failure."""
    intimation = {
        "id": "test-id",
        "url_documento": "https://example.com/doc.pdf",
    }
    mock_doc_service.download_pdf.return_value = None

    await _process_intimation(
        intimation,
        mock_doc_service,
        mock_ia_service,
        mock_repository,
        False,
    )

    # Should not attempt upload
    mock_ia_service.upload_file.assert_not_called()
