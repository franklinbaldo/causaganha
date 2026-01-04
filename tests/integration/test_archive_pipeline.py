"""Integration tests for archive pipeline (RED phase)."""

from unittest.mock import AsyncMock, patch

import pytest

from causaganha.domain.models import Intimation
from causaganha.pipeline.archive import run_archive
from datetime import date


@pytest.fixture
def mock_repository():
    return AsyncMock()


@pytest.fixture
def mock_doc_service():
    service = AsyncMock()
    service.download_pdf.return_value = b"PDF CONTENT"
    return service


@pytest.fixture
def mock_archive_service():
    service = AsyncMock()
    service.upload_file.return_value = "https://archive.org/details/test"
    service.generate_metadata.return_value = {}
    return service


@pytest.mark.asyncio
async def test_run_archive_success(mock_repository, mock_doc_service, mock_archive_service):
    """Pipeline should fetch unarchived, download, and upload."""
    # Arrange
    intimation = Intimation(
        id=1,
        numero_processo="123",
        sigla_tribunal="TJRO",
        data_disponibilizacao=date(2024, 1, 1),
        link="http://example.com/1.pdf",
        tipo_comunicacao="Int",
        nome_orgao="Org",
        texto="Txt",
        tipo_documento="Doc",
        nome_classe="Class",
        hash="abc"
    )
    mock_repository.get_unarchived_intimations.return_value = [intimation]

    # Act
    await run_archive(mock_repository, mock_doc_service, mock_archive_service, limit=1)

    # Assert
    mock_repository.get_unarchived_intimations.assert_called_once_with(limit=1)
    mock_doc_service.download_pdf.assert_called_once_with("http://example.com/1.pdf")
    mock_archive_service.upload_file.assert_called_once()
    mock_repository.mark_as_archived.assert_called_once_with("1", "https://archive.org/details/test")


@pytest.mark.asyncio
async def test_run_archive_dry_run(mock_repository, mock_doc_service, mock_archive_service):
    """Dry run should download but NOT upload or mark archived."""
    # Arrange
    intimation = Intimation(
        id=1,
        numero_processo="123",
        sigla_tribunal="TJRO",
        data_disponibilizacao=date(2024, 1, 1),
        link="http://example.com/1.pdf",
        tipo_comunicacao="Int",
        nome_orgao="Org",
        texto="Txt",
        tipo_documento="Doc",
        nome_classe="Class",
        hash="abc"
    )
    mock_repository.get_unarchived_intimations.return_value = [intimation]

    # Act
    await run_archive(mock_repository, mock_doc_service, mock_archive_service, limit=1, dry_run=True)

    # Assert
    mock_doc_service.download_pdf.assert_called_once()
    mock_archive_service.upload_file.assert_not_called()
    mock_repository.mark_as_archived.assert_not_called()


@pytest.mark.asyncio
async def test_process_intimation_no_url(mock_repository, mock_doc_service, mock_archive_service):
    """Should skip intimations without URL."""
    # Arrange
    intimation = Intimation(
        id=1,
        numero_processo="123",
        sigla_tribunal="TJRO",
        data_disponibilizacao=date(2024, 1, 1),
        link=None,
        tipo_comunicacao="Int",
        nome_orgao="Org",
        texto="Txt",
        tipo_documento="Doc",
        nome_classe="Class",
        hash="abc"
    )
    mock_repository.get_unarchived_intimations.return_value = [intimation]

    # Act
    await run_archive(mock_repository, mock_doc_service, mock_archive_service, limit=1)

    # Assert
    mock_doc_service.download_pdf.assert_not_called()


@pytest.mark.asyncio
async def test_process_intimation_download_failure(mock_repository, mock_doc_service, mock_archive_service):
    """Should handle download failure gracefully."""
    # Arrange
    intimation = Intimation(
        id=1,
        numero_processo="123",
        sigla_tribunal="TJRO",
        data_disponibilizacao=date(2024, 1, 1),
        link="http://example.com/fail.pdf",
        tipo_comunicacao="Int",
        nome_orgao="Org",
        texto="Txt",
        tipo_documento="Doc",
        nome_classe="Class",
        hash="abc"
    )
    mock_repository.get_unarchived_intimations.return_value = [intimation]
    mock_doc_service.download_pdf.return_value = None

    # Act
    await run_archive(mock_repository, mock_doc_service, mock_archive_service, limit=1)

    # Assert
    mock_doc_service.download_pdf.assert_called_once()
    mock_archive_service.upload_file.assert_not_called()
    mock_repository.mark_as_archived.assert_not_called()
