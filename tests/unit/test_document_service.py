import httpx
import pytest
from unittest.mock import AsyncMock, Mock, patch
from structlog.testing import capture_logs
from causaganha.services.document import DocumentService

@pytest.fixture
def service():
    return DocumentService()

@pytest.mark.asyncio
async def test_download_pdf_success(service):
    """Test successful PDF download."""
    content = b"%PDF-1.4..."

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = content
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.raise_for_status = Mock()

        mock_client.request.return_value = mock_response

        result = await service.download_pdf("http://example.com/doc.pdf")

        assert result == content
        mock_client.request.assert_awaited_once_with(
            "GET", "http://example.com/doc.pdf", follow_redirects=True, timeout=30.0
        )
        mock_response.raise_for_status.assert_called_once()

@pytest.mark.asyncio
async def test_download_pdf_not_pdf_warning(service):
    """Test warning when content type is not PDF."""
    content = b"<html>...</html>"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = content
        mock_response.headers = {"content-type": "text/html"}

        mock_client.request.return_value = mock_response

        with capture_logs() as cap_logs:
            result = await service.download_pdf("http://example.com/doc.html")

            assert result == content # Still returns content
            assert any(log["event"] == "url_not_pdf" for log in cap_logs)

@pytest.mark.asyncio
async def test_download_pdf_failure(service):
    """Test failure during download."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        mock_client.request.side_effect = Exception("Connection error")

        with capture_logs() as cap_logs:
            result = await service.download_pdf("http://example.com/doc.pdf")

            assert result is None
            assert any(log["event"] == "download_failed" for log in cap_logs)

@pytest.mark.asyncio
async def test_download_pdf_timeout(service):
    """Test timeout during download."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # Simulate timeout
        mock_client.request.side_effect = httpx.TimeoutException("Timeout")

        with capture_logs() as cap_logs:
            result = await service.download_pdf("http://example.com/doc.pdf")

            assert result is None
            assert any(log["event"] == "download_failed" for log in cap_logs)
            # Verify exception info is captured
            assert any(log.get("exc_info") for log in cap_logs if log["event"] == "download_failed")

@pytest.mark.asyncio
async def test_download_pdf_http_error(service):
    """Test HTTP error (e.g. 404, 500) during download."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        mock_response = Mock()
        mock_response.status_code = 404
        # The service calls raise_for_status(), which raises HTTPStatusError
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=mock_response
        )

        mock_client.request.return_value = mock_response

        with capture_logs() as cap_logs:
            result = await service.download_pdf("http://example.com/doc.pdf")

            assert result is None
            assert any(log["event"] == "download_failed" for log in cap_logs)
