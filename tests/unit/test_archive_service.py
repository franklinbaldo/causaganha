"""Tests for Internet Archive service."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from causaganha.services.archive import InternetArchiveService


@pytest.fixture
def ia_service():
    """Create an Internet Archive service instance."""
    return InternetArchiveService()


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary test file."""
    test_file = tmp_path / "test.pdf"
    test_file.write_text("test content")
    return test_file


@pytest.mark.asyncio
async def test_upload_file_success(ia_service, temp_file):
    """Test successful file upload."""
    with patch.object(ia_service, "_sync_upload", return_value="https://archive.org/details/test-item"):
        result = await ia_service.upload_file(
            temp_file,
            "test-item",
            {"title": "Test"}
        )
        assert result == "https://archive.org/details/test-item"


@pytest.mark.asyncio
async def test_upload_file_not_found(ia_service):
    """Test upload with non-existent file."""
    result = await ia_service.upload_file(
        Path("/nonexistent/file.pdf"),
        "test-item",
        {}
    )
    assert result is None


@pytest.mark.asyncio
async def test_upload_file_exception(ia_service, temp_file):
    """Test upload with exception."""
    with patch.object(ia_service, "_sync_upload", side_effect=Exception("Upload failed")):
        result = await ia_service.upload_file(
            temp_file,
            "test-item",
            {}
        )
        assert result is None


@pytest.mark.asyncio
async def test_check_item_exists_true(ia_service):
    """Test checking if item exists."""
    with patch.object(ia_service, "_sync_check_item", return_value=True):
        result = await ia_service.check_item_exists("test-item")
        assert result is True


@pytest.mark.asyncio
async def test_check_item_exists_false(ia_service):
    """Test checking if item doesn't exist."""
    with patch.object(ia_service, "_sync_check_item", return_value=False):
        result = await ia_service.check_item_exists("test-item")
        assert result is False


@pytest.mark.asyncio
async def test_check_item_exception(ia_service):
    """Test check with exception."""
    with patch.object(ia_service, "_sync_check_item", side_effect=Exception("Check failed")):
        result = await ia_service.check_item_exists("test-item")
        assert result is False
