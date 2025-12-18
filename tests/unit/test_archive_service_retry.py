"""Tests for Internet Archive service retry logic."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from causaganha.services.archive import InternetArchiveService

@pytest.fixture
def ia_service():
    """Create an Internet Archive service instance with low retry delay."""
    return InternetArchiveService(upload_settings={
        "retries": 3,
        "retries_sleep": 0.01,  # fast tests
        "timeout": 1
    })

@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary test file."""
    test_file = tmp_path / "test.pdf"
    test_file.write_text("test content")
    return test_file

@pytest.mark.asyncio
async def test_upload_retry_success(ia_service, temp_file):
    """Test that upload retries on transient errors and eventually succeeds."""
    # Mock _sync_upload to fail twice then succeed
    mock_sync_upload = MagicMock(side_effect=[
        TimeoutError("Timeout 1"),
        ConnectionError("Connection lost"),
        "https://archive.org/details/test-item"
    ])

    with patch.object(ia_service, "_sync_upload", side_effect=mock_sync_upload) as mock_method:
        result = await ia_service.upload_file(
            temp_file,
            "test-item",
            {"title": "Test"}
        )

        assert result == "https://archive.org/details/test-item"
        assert mock_method.call_count == 3

@pytest.mark.asyncio
async def test_upload_retry_failure(ia_service, temp_file):
    """Test that upload gives up after max retries."""
    # Mock _sync_upload to always fail with TimeoutError
    mock_sync_upload = MagicMock(side_effect=TimeoutError("Timeout"))

    with patch.object(ia_service, "_sync_upload", side_effect=mock_sync_upload) as mock_method:
        result = await ia_service.upload_file(
            temp_file,
            "test-item",
            {"title": "Test"}
        )

        assert result is None
        assert mock_method.call_count == 3  # Max retries

@pytest.mark.asyncio
async def test_upload_no_retry_on_fatal_error(ia_service, temp_file):
    """Test that upload does NOT retry on non-transient errors."""
    # Mock _sync_upload to fail with a generic Exception (treated as fatal)
    mock_sync_upload = MagicMock(side_effect=ValueError("Invalid data"))

    with patch.object(ia_service, "_sync_upload", side_effect=mock_sync_upload) as mock_method:
        result = await ia_service.upload_file(
            temp_file,
            "test-item",
            {"title": "Test"}
        )

        assert result is None
        assert mock_method.call_count == 1  # Should stop after first error
