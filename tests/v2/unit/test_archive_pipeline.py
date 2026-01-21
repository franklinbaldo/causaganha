"""Unit tests for the archive pipeline."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from causaganha.v2.pipeline.archive import archive_documents


@pytest.mark.asyncio
async def test_archive_documents_success() -> None:
    """Test archive_documents successfully archives items."""
    # Mocks
    mock_doc_service = Mock()
    mock_doc_service.download_pdf = AsyncMock(return_value=b"PDF CONTENT")

    mock_archive_service = Mock()
    mock_archive_service.generate_metadata.return_value = {"title": "Test"}

    mock_preservation = AsyncMock()
    mock_preservation.preserve_document.return_value = "https://archive.org/item"

    with (
        patch("causaganha.v2.pipeline.archive.get_connection") as mock_get_conn,
        patch("causaganha.v2.pipeline.archive.get_unarchived_intimations") as mock_get_unarchived,
        patch("causaganha.v2.pipeline.archive.mark_as_archived") as mock_mark,
        patch("causaganha.v2.pipeline.archive.PreservationService") as mock_preservation_cls,
    ):
        # Setup DB mocks
        mock_get_unarchived.return_value = [
            {
                "id": 1,
                "link": "http://example.com/1.pdf",
                "sigla_tribunal": "TJRO",
                "numero_processo": "123",
            },
        ]

        # Setup Service mocks
        mock_preservation_instance = mock_preservation_cls.return_value
        mock_preservation_instance.preserve_document = AsyncMock(return_value="https://ia/1")

        # Run
        result = await archive_documents(
            mock_doc_service,
            mock_archive_service,
            limit=1,
        )

        assert result["status"] == "success"
        assert result["archived"] == 1

        mock_preservation_instance.preserve_document.assert_called_once()
        mock_mark.assert_called_once()


@pytest.mark.asyncio
async def test_archive_documents_no_items() -> None:
    """Test archive_documents with no pending items."""
    mock_doc_service = Mock()
    mock_archive_service = Mock()

    with (
        patch("causaganha.v2.pipeline.archive.get_connection"),
        patch("causaganha.v2.pipeline.archive.get_unarchived_intimations") as mock_get_unarchived,
    ):
        mock_get_unarchived.return_value = []

        result = await archive_documents(
            mock_doc_service,
            mock_archive_service,
        )

        assert result["archived"] == 0
