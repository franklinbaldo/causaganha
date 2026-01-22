"""Tests for Internet Archive Parquet Downloader."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from causaganha.v2.pipeline.ia_download import (
    IAParquetDownloader,
    DownloadConfig,
)


@pytest.fixture
def download_config(tmp_path):
    """Create test download config."""
    return DownloadConfig(
        cache_dir=tmp_path / "cache",
        max_retries=2,
        cache_ttl_days=7,
    )


@pytest.fixture
def downloader(download_config):
    """Create downloader instance."""
    return IAParquetDownloader(config=download_config)


class TestIAParquetDownloader:
    """Test suite for IAParquetDownloader."""

    def test_init(self, downloader, download_config):
        """Test downloader initialization."""
        assert downloader.config == download_config
        assert download_config.cache_dir.exists()

    def test_generate_item_id(self, downloader):
        """Test IA item ID generation."""
        item_id = downloader._generate_item_id("2025-01-15", "TJRO")
        assert item_id == "causaganha-2025-01-15-TJRO"

    def test_generate_filename(self, downloader):
        """Test parquet filename generation."""
        filename = downloader._generate_filename("2025-01-15", "TJRO")
        assert filename == "causaganha-2025-01-15-TJRO.parquet"

    @pytest.mark.asyncio
    async def test_get_item_url(self, downloader):
        """Test IA item URL generation."""
        url = await downloader.get_item_url("TJRO", "2025-01-15")
        assert url == "https://archive.org/details/causaganha-2025-01-15-TJRO"

    def test_get_cached_file_not_exists(self, downloader):
        """Test cache check when file doesn't exist."""
        cached = downloader._get_cached_file("TJRO", "2025-01-15")
        assert cached is None

    def test_get_cached_file_exists(self, downloader, download_config):
        """Test cache check when file exists and is fresh."""
        # Create cached file
        cache_file = download_config.cache_dir / "causaganha-2025-01-15-TJRO.parquet"
        cache_file.write_text("fake parquet data")

        cached = downloader._get_cached_file("TJRO", "2025-01-15")
        assert cached == cache_file

    def test_clear_cache(self, downloader, download_config):
        """Test cache clearing."""
        # Create some cached files
        for i in range(3):
            cache_file = download_config.cache_dir / f"causaganha-2025-01-{i+10}-TJRO.parquet"
            cache_file.write_text("fake data")

        deleted = downloader.clear_cache()
        assert deleted == 3
        assert len(list(download_config.cache_dir.glob("*.parquet"))) == 0

    @pytest.mark.asyncio
    async def test_download_invalid_date(self, downloader):
        """Test download with invalid date format."""
        with pytest.raises(ValueError, match="Invalid date format"):
            await downloader.download("TJRO", "2025-13-45")

    @pytest.mark.asyncio
    async def test_download_range_invalid(self, downloader):
        """Test download range with invalid dates."""
        with pytest.raises(ValueError):
            await downloader.download_range(
                start_date="2025-01-20",
                end_date="2025-01-10",
                tribunal="TJRO",
            )

    @pytest.mark.asyncio
    async def test_check_exists_with_mock(self, downloader):
        """Test check_exists with mocked IA."""
        with patch("causaganha.v2.pipeline.ia_download.ia.get_item") as mock_get_item:
            # Mock item that exists
            mock_item = MagicMock()
            mock_item.exists = True
            mock_item.files = [{"name": "causaganha-2025-01-15-TJRO.parquet"}]
            mock_get_item.return_value = mock_item

            exists = await downloader.check_exists("TJRO", "2025-01-15")
            assert exists is True

    @pytest.mark.asyncio
    async def test_check_exists_not_found(self, downloader):
        """Test check_exists when item doesn't exist."""
        with patch("causaganha.v2.pipeline.ia_download.ia.get_item") as mock_get_item:
            # Mock item that doesn't exist
            mock_item = MagicMock()
            mock_item.exists = False
            mock_get_item.return_value = mock_item

            exists = await downloader.check_exists("TJRO", "2025-01-15")
            assert exists is False


class TestDownloadConfig:
    """Test suite for DownloadConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = DownloadConfig()
        assert config.cache_dir == Path("./ia_cache")
        assert config.max_retries == 3
        assert config.retry_backoff == 2.0
        assert config.cache_ttl_days == 30

    def test_custom_config(self, tmp_path):
        """Test custom configuration."""
        cache_dir = tmp_path / "custom_cache"
        config = DownloadConfig(
            cache_dir=cache_dir,
            max_retries=5,
            cache_ttl_days=60,
        )
        assert config.cache_dir == cache_dir
        assert config.max_retries == 5
        assert config.cache_ttl_days == 60
        assert cache_dir.exists()
