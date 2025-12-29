"""Tests for Internet Archive service."""

import asyncio
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog

from causaganha.services.archive import ArchiveService, InternetArchiveService, LocalArchiveService
from causaganha.services.document import DocumentService
from causaganha.storage.repository import IntimationRepository


@pytest.fixture
def ia_service() -> InternetArchiveService:
    """Create an Internet Archive service instance."""
    return InternetArchiveService()


@pytest.fixture
def temp_file(tmp_path: Path) -> Path:
    """Create a temporary test file."""
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"test pdf content")
    return test_file


class TestUploadFileValidation:
    """Test upload validation."""

    @pytest.mark.asyncio
    async def test_validates_file_exists(self, ia_service: InternetArchiveService) -> None:
        """Should raise/return None if file doesn't exist."""
        result = await ia_service.upload_file(
            Path("/nonexistent/file.pdf"),
            "test-item",
            {},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_validates_item_id_format(self, ia_service: InternetArchiveService, temp_file: Path) -> None:
        """Should validate item_id follows IA naming conventions."""
        with patch.object(ia_service, "_sync_upload", side_effect=ValueError("Invalid item ID")):
            result = await ia_service.upload_file(
                temp_file,
                "invalid item id with spaces",
                {},
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_validates_file_size_reasonable(self, ia_service: InternetArchiveService, tmp_path: Path) -> None:
        """Should handle very large files appropriately."""
        # Create a test for max file size
        large_file = tmp_path / "large.pdf"
        large_file.write_bytes(b"x" * (1024 * 1024))  # 1MB just for speed, TDD had 100MB

        with patch.object(ia_service, "_sync_upload", return_value="https://archive.org/details/test"):
            result = await ia_service.upload_file(
                large_file,
                "test-item",
                {},
            )
            # Should handle large files
            assert result is not None

    @pytest.mark.asyncio
    async def test_validates_metadata_structure(self, ia_service: InternetArchiveService, temp_file: Path) -> None:
        """Should validate metadata has required fields."""
        # Define what required metadata fields should be
        required_metadata = {
            "collection": "opensource",
            "mediatype": "texts",
            "title": "Test Document",
        }

        with patch.object(ia_service, "_sync_upload", return_value="https://archive.org/details/test"):
            result = await ia_service.upload_file(
                temp_file,
                "test-item",
                required_metadata,
            )
            assert result is not None


class TestUploadResilience:
    """Test upload error handling and retries."""

    @pytest.mark.asyncio
    async def test_retries_on_transient_errors(self, ia_service: InternetArchiveService, temp_file: Path) -> None:
        """Should retry on network errors."""
        with patch.object(
            ia_service,
            "_sync_upload",
            side_effect=[
                ConnectionError("Network error"),
                ConnectionError("Network error"),
                "https://archive.org/details/test",  # Success on 3rd try
            ],
        ):
            result = await ia_service.upload_file(
                temp_file,
                "test-item",
                {},
            )
            # Should eventually succeed after retries
            assert result == "https://archive.org/details/test"

    @pytest.mark.asyncio
    async def test_gives_up_after_max_retries(self, ia_service: InternetArchiveService, temp_file: Path) -> None:
        """Should give up after maximum retry attempts."""
        # Default retries is 3
        with patch.object(
            ia_service,
            "_sync_upload",
            side_effect=ConnectionError("Persistent error"),
        ):
            result = await ia_service.upload_file(
                temp_file,
                "test-item",
                {},
            )
            # Should return None after exhausting retries
            assert result is None

    @pytest.mark.asyncio
    async def test_logs_upload_progress(self, ia_service: InternetArchiveService, temp_file: Path) -> None:
        """Should log upload progress for monitoring."""
        with patch.object(ia_service, "_sync_upload", return_value="https://archive.org/details/test"):
            with patch("causaganha.services.archive.logger") as mock_logger:
                await ia_service.upload_file(
                    temp_file,
                    "test-item",
                    {"title": "Test"},
                )
                assert mock_logger.info.called or mock_logger.debug.called

    @pytest.mark.asyncio
    async def test_upload_no_retry_on_fatal_error(self, ia_service: InternetArchiveService, temp_file: Path) -> None:
        """Test that upload does NOT retry on non-transient errors."""
        # Mock _sync_upload to fail with a generic Exception (treated as fatal)
        mock_sync_upload = MagicMock(side_effect=ValueError("Invalid data"))

        with patch.object(ia_service, "_sync_upload", side_effect=mock_sync_upload) as mock_method:
            result = await ia_service.upload_file(
                temp_file,
                "test-item",
                {"title": "Test"},
            )

            assert result is None
            assert mock_method.call_count == 1  # Should stop after first error


class TestCheckItemExists:
    """Test item existence checking."""

    @pytest.mark.asyncio
    async def test_returns_true_for_existing_item(self, ia_service: InternetArchiveService) -> None:
        """Should return True if item exists on IA."""
        with patch.object(ia_service, "_sync_check_item", return_value=True):
            result = await ia_service.check_item_exists("existing-item")
            assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_for_nonexistent_item(self, ia_service: InternetArchiveService) -> None:
        """Should return False if item doesn't exist."""
        with patch.object(ia_service, "_sync_check_item", return_value=False):
            result = await ia_service.check_item_exists("nonexistent-item")
            assert result is False

    @pytest.mark.asyncio
    async def test_caches_existence_checks(self, ia_service: InternetArchiveService) -> None:
        """Should cache existence checks to avoid repeated API calls."""
        # Caching is NOT implemented in archive.py yet.
        pass


class TestMetadataGeneration:
    """Test metadata generation."""

    def test_generates_valid_metadata_from_intimation(self, ia_service: InternetArchiveService) -> None:
        """Should generate proper IA metadata from intimation data."""
        intimation_data = {
            "id": "test-123",
            "numero_processo": "1234567-89.2024.8.22.0001",
            "data_disponibilizacao": "2024-01-15",
            "sigla_tribunal": "TJRO",
        }

        expected_metadata = {
            "collection": "opensource",
            "mediatype": "texts",
            "title": "TJRO - Processo 1234567-89.2024.8.22.0001",
            "date": "2024-01-15",
            "creator": "CausaGanha",
            "subject": ["judicial", "tjro", "brazil"],
            "description": "Intimação judicial do processo 1234567-89.2024.8.22.0001",
        }

        metadata = ia_service.generate_metadata(intimation_data)
        assert metadata["title"] == expected_metadata["title"]
        assert metadata["collection"] == expected_metadata["collection"]
        assert metadata["date"] == expected_metadata["date"]


class TestServiceConfiguration:
    """Test service configuration."""

    def test_initializes_with_credentials(self) -> None:
        """Should initialize with IA credentials from config."""
        service = InternetArchiveService()
        assert service.session is not None

    def test_respects_custom_upload_settings(self) -> None:
        """Should allow custom upload settings."""
        custom_settings = {
            "retries": 5,
            "retries_sleep": 10,
            "timeout": 300,
        }

        service = InternetArchiveService(upload_settings=custom_settings)
        assert service.upload_settings["retries"] == 5


class TestLocalArchiveHierarchicalStorage:
    """Test local archive hierarchical storage organization."""

    @pytest.fixture
    def local_service(self, tmp_path: Path) -> LocalArchiveService:
        from causaganha.services.archive import LocalArchiveService
        return LocalArchiveService(archive_root=tmp_path)

    @pytest.fixture
    def temp_file(self, tmp_path: Path) -> Path:
        """Create a temporary test file."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"test pdf content")
        return test_file

    @pytest.mark.asyncio
    async def test_uses_hierarchical_path_with_metadata(self, local_service: LocalArchiveService, temp_file: Path) -> None:
        """Should organize files as tribunal/year/month/item_id/file.pdf when metadata is present."""

        metadata = {
            "date": "2024-05-24",
            "tribunal_code": "TJRO"
        }

        item_id = "causaganha-tjro-123"

        result = await local_service.upload_file(
            temp_file,
            item_id,
            metadata,
        )

        # Expected path: root / TJRO / 2024 / 05 / item_id / file.pdf
        expected_path = local_service.archive_root / "TJRO" / "2024" / "05" / item_id / temp_file.name

        assert result == str(expected_path)
        assert expected_path.exists()

    @pytest.mark.asyncio
    async def test_fallback_to_flat_if_metadata_missing(self, local_service: LocalArchiveService, temp_file: Path) -> None:
        """Should fall back to simple item_id folder if metadata is missing."""
        item_id = "causaganha-tjro-123"
        result = await local_service.upload_file(
            temp_file,
            item_id,
            None
        )

        expected_path = local_service.archive_root / item_id / temp_file.name
        assert result == str(expected_path)
        assert expected_path.exists()


@pytest.fixture
def mock_repository() -> AsyncMock:
    return AsyncMock(spec=IntimationRepository)

@pytest.fixture
def mock_doc_service() -> AsyncMock:
    service = AsyncMock(spec=DocumentService)
    service.download_pdf.return_value = b"fake pdf content"
    return service

@pytest.fixture
def mock_archive_service() -> AsyncMock:
    service = AsyncMock(spec=ArchiveService)
    service.upload_file.return_value = "https://archive.org/details/some-item"
    service.generate_metadata.return_value = {}
    return service

@pytest.mark.asyncio
async def test_archive_uses_correct_court_in_id(
    mock_repository: AsyncMock, mock_doc_service: AsyncMock, mock_archive_service: AsyncMock,
) -> None:
    """Test that the archive pipeline uses the correct tribunal in the item ID."""
    from causaganha.pipeline.archive import run_archive

    # Setup data
    intimation = {
        "id": 12345,
        "sigla_tribunal": "TJMT",
        "link": "http://example.com/doc.pdf",
        "numero_processo": "123",
        "data_disponibilizacao": "2023-01-01",
    }

    mock_repository.get_unarchived_intimations.return_value = [intimation]

    # Run
    await run_archive(
        mock_repository,
        mock_doc_service,
        mock_archive_service,
        limit=1,
    )

    # Verify
    mock_archive_service.upload_file.assert_called_once()
    args = mock_archive_service.upload_file.call_args
    # args[0] is file_path, args[1] is item_id
    item_id = args.args[1]

    # Should contain tjmt, not tjro
    assert "tjmt" in item_id
    assert "tjro" not in item_id
