"""Tests for DocumentService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from causaganha.clients.document import DocumentService


@pytest.fixture
def doc_service():
    """Create document service."""
    return DocumentService()


@pytest.mark.asyncio
async def test_download_pdf_success(doc_service) -> None:
    """Test successful PDF download."""
    url = "http://example.com/doc.pdf"
    content = b"%PDF-1.4..."

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = content
    mock_resp.headers = {"content-type": "application/pdf"}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.request.return_value = mock_resp
    # Context manager setup for async client
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await doc_service.download_pdf(url)
        assert result == content


@pytest.mark.asyncio
async def test_download_pdf_not_pdf_warning(doc_service) -> None:
    """Test warning when content type is not PDF."""
    url = "http://example.com/doc.html"
    content = b"<html>...</html>"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = content
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.request.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        # We want to verify the warning log, but for now just check it returns content
        result = await doc_service.download_pdf(url)
        assert result == content


@pytest.mark.asyncio
async def test_download_pdf_failure(doc_service) -> None:
    """Test failed download."""
    url = "http://example.com/error"

    mock_client = AsyncMock()
    # Simulate exception
    mock_client.request.side_effect = Exception("Network error")
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await doc_service.download_pdf(url)
        assert result is None
