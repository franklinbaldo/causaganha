"""Internet Archive Parquet Downloader

Downloads parquet files from Internet Archive for reanalysis workflows.
Supports local caching, batch downloads, and retry logic.

Usage:
    downloader = IAParquetDownloader(cache_dir="./cache")
    file_path = await downloader.download(tribunal="TJRO", date="2025-01-15")
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import internetarchive as ia


logger = logging.getLogger(__name__)


@dataclass
class DownloadConfig:
    """Configuration for Internet Archive downloads."""

    cache_dir: Path = Path("./ia_cache")
    max_retries: int = 3
    retry_backoff: float = 2.0  # Exponential backoff multiplier
    initial_retry_delay: float = 2.0  # Seconds
    verify_checksum: bool = True
    cache_ttl_days: int = 30  # Cache expiry in days

    def __post_init__(self):
        """Ensure cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)


class IAParquetDownloader:
    """Downloads CausaGanha parquet files from Internet Archive."""

    def __init__(
        self,
        config: DownloadConfig | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
    ):
        """Initialize Internet Archive downloader.

        Args:
            config: Download configuration (uses defaults if None)
            access_key: IA access key (uses env var if None)
            secret_key: IA secret key (uses env var if None)

        Note:
            Credentials can be configured via:
            - Environment variables: IA_ACCESS_KEY, IA_SECRET_KEY
            - Config file: ~/.config/ia.ini
            - Parameters passed here
        """
        self.config = config or DownloadConfig()

        # Configure IA session with credentials if provided
        if access_key and secret_key:
            ia.configure(access_key, secret_key)

        logger.info(
            f"IAParquetDownloader initialized with cache_dir={self.config.cache_dir}",
        )

    async def download(
        self,
        tribunal: str,
        date: str,
        force_refresh: bool = False,
    ) -> Path:
        """Download parquet file for a specific date and tribunal.

        Args:
            tribunal: Tribunal code (e.g., TJRO, TJSP)
            date: Date in YYYY-MM-DD format
            force_refresh: Skip cache and force re-download

        Returns:
            Path to downloaded parquet file

        Raises:
            ValueError: If date format invalid or item not found
            IOError: If download fails after retries
        """
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Invalid date format. Expected YYYY-MM-DD: {e}") from e

        # Check cache first
        if not force_refresh:
            cached_file = self._get_cached_file(tribunal, date)
            if cached_file:
                logger.info(f"Using cached file: {cached_file}")
                return cached_file

        # Generate IA item ID and filename
        item_id = self._generate_item_id(date, tribunal)
        filename = self._generate_filename(date, tribunal)

        logger.info(f"Downloading {filename} from IA item: {item_id}")

        # Download with retry logic
        for attempt in range(self.config.max_retries):
            try:
                # Run blocking IA download in thread pool
                file_path = await asyncio.to_thread(
                    self._download_file,
                    item_id,
                    filename,
                )

                # Verify checksum if configured
                if self.config.verify_checksum:
                    await self._verify_file(file_path, item_id, filename)

                logger.info(f"Successfully downloaded to {file_path}")
                return file_path

            except Exception as e:
                logger.warning(
                    f"Download attempt {attempt + 1}/{self.config.max_retries} failed: {e}",
                )

                if attempt < self.config.max_retries - 1:
                    # Calculate exponential backoff delay
                    delay = self.config.initial_retry_delay * (
                        self.config.retry_backoff**attempt
                    )
                    logger.info(f"Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed
                    raise OSError(
                        f"Failed to download after {self.config.max_retries} attempts: {e}",
                    ) from e

    async def download_range(
        self,
        start_date: str,
        end_date: str,
        tribunal: str,
        skip_missing: bool = True,
    ) -> list[Path]:
        """Download parquet files for a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (inclusive)
            tribunal: Tribunal code (e.g., TJRO)
            skip_missing: Continue if some dates are missing

        Returns:
            List of downloaded file paths

        Raises:
            ValueError: If date range invalid
            IOError: If any download fails and skip_missing=False
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"Invalid date format. Expected YYYY-MM-DD: {e}",
            ) from e

        if start > end:
            raise ValueError("start_date must be before or equal to end_date")

        logger.info(
            f"Downloading {tribunal} parquet files from {start_date} to {end_date}",
        )

        # Generate date range
        current = start
        dates = []
        while current <= end:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        logger.info(f"Downloading {len(dates)} files for {tribunal}")

        # Download files
        downloaded_files = []
        failed_downloads = []

        for date in dates:
            try:
                file_path = await self.download(tribunal, date)
                downloaded_files.append(file_path)
            except Exception as e:
                logger.error(f"Failed to download {tribunal} for {date}: {e}")
                failed_downloads.append((date, str(e)))

                if not skip_missing:
                    raise OSError(
                        f"Download failed for {date}: {e}",
                    ) from e

        logger.info(
            f"Downloaded {len(downloaded_files)}/{len(dates)} files. "
            f"Failed: {len(failed_downloads)}",
        )

        if failed_downloads:
            logger.warning(
                f"Failed downloads: {', '.join(date for date, _ in failed_downloads)}",
            )

        return downloaded_files

    async def check_exists(self, tribunal: str, date: str) -> bool:
        """Check if parquet file exists on Internet Archive.

        Args:
            tribunal: Tribunal code
            date: Date in YYYY-MM-DD format

        Returns:
            True if item exists, False otherwise
        """
        item_id = self._generate_item_id(date, tribunal)
        filename = self._generate_filename(date, tribunal)

        try:
            item = await asyncio.to_thread(ia.get_item, item_id)

            if not item.exists:
                return False

            # Check if specific file exists in item
            for file in item.files:
                if file["name"] == filename:
                    return True

            return False

        except Exception as e:
            logger.warning(f"Error checking if item exists: {e}")
            return False

    def _download_file(self, item_id: str, filename: str) -> Path:
        """Download file from Internet Archive (blocking call).

        Args:
            item_id: IA item identifier
            filename: Filename to download

        Returns:
            Path to downloaded file

        Raises:
            Exception: If download fails or item not found
        """
        # Get IA item
        item = ia.get_item(item_id)

        if not item.exists:
            raise ValueError(f"Item not found on Internet Archive: {item_id}")

        # Check if file exists in item
        file_found = False
        for file in item.files:
            if file["name"] == filename:
                file_found = True
                break

        if not file_found:
            raise ValueError(f"File {filename} not found in item {item_id}")

        # Download file to cache directory
        output_path = self.config.cache_dir / filename

        # Download using IA library
        item.download(
            files=[filename],
            destdir=str(self.config.cache_dir),
            verbose=False,
            ignore_existing=False,  # Always re-download if not cached
        )

        if not output_path.exists():
            raise OSError(f"Download completed but file not found: {output_path}")

        return output_path

    async def _verify_file(self, file_path: Path, item_id: str, filename: str) -> None:
        """Verify downloaded file using checksum.

        Args:
            file_path: Path to downloaded file
            item_id: IA item identifier
            filename: Filename

        Raises:
            IOError: If verification fails
        """
        logger.debug(f"Verifying checksum for {filename}")

        try:
            # Get item metadata
            item = await asyncio.to_thread(ia.get_item, item_id)

            # Find file metadata
            file_meta = None
            for file in item.files:
                if file["name"] == filename:
                    file_meta = file
                    break

            if not file_meta:
                logger.warning(f"Could not find file metadata for {filename}")
                return

            # Verify MD5 checksum if available
            if "md5" in file_meta:
                expected_md5 = file_meta["md5"]
                actual_md5 = await self._calculate_md5(file_path)

                if actual_md5 != expected_md5:
                    raise OSError(
                        f"Checksum mismatch: expected {expected_md5}, got {actual_md5}",
                    )

                logger.debug(f"Checksum verified: {actual_md5}")

        except Exception as e:
            logger.warning(f"Verification failed: {e}")
            # Don't fail download on verification error, just log

    async def _calculate_md5(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file.

        Args:
            file_path: Path to file

        Returns:
            MD5 checksum as hex string
        """

        def _calculate():
            md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    md5.update(chunk)
            return md5.hexdigest()

        return await asyncio.to_thread(_calculate)

    def _get_cached_file(self, tribunal: str, date: str) -> Path | None:
        """Check if file exists in cache and is not expired.

        Args:
            tribunal: Tribunal code
            date: Date in YYYY-MM-DD format

        Returns:
            Path to cached file if valid, None otherwise
        """
        filename = self._generate_filename(date, tribunal)
        cache_path = self.config.cache_dir / filename

        if not cache_path.exists():
            return None

        # Check if cache is expired
        file_age_days = (
            datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
        ).days

        if file_age_days > self.config.cache_ttl_days:
            logger.info(
                f"Cache expired for {filename} (age: {file_age_days} days)",
            )
            return None

        return cache_path

    def clear_cache(self, older_than_days: int | None = None) -> int:
        """Clear cached parquet files.

        Args:
            older_than_days: Only delete files older than N days (None = all)

        Returns:
            Number of files deleted
        """
        deleted = 0

        for file_path in self.config.cache_dir.glob("causaganha-*.parquet"):
            if older_than_days is None:
                file_path.unlink()
                deleted += 1
            else:
                file_age_days = (
                    datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
                ).days

                if file_age_days > older_than_days:
                    file_path.unlink()
                    deleted += 1

        logger.info(f"Cleared {deleted} cached files")
        return deleted

    def _generate_item_id(self, date: str, tribunal: str) -> str:
        """Generate Internet Archive item ID.

        Args:
            date: Partition date (YYYY-MM-DD)
            tribunal: Tribunal code

        Returns:
            Item ID: causaganha-2025-01-15-TJRO
        """
        return f"causaganha-{date}-{tribunal}"

    def _generate_filename(self, date: str, tribunal: str) -> str:
        """Generate parquet filename.

        Args:
            date: Partition date (YYYY-MM-DD)
            tribunal: Tribunal code

        Returns:
            Filename: causaganha-2025-01-15-TJRO.parquet
        """
        return f"causaganha-{date}-{tribunal}.parquet"

    async def get_item_url(self, tribunal: str, date: str) -> str:
        """Get Internet Archive URL for an item.

        Args:
            tribunal: Tribunal code
            date: Date in YYYY-MM-DD format

        Returns:
            IA item URL
        """
        item_id = self._generate_item_id(date, tribunal)
        return f"https://archive.org/details/{item_id}"
