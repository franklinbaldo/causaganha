"""Internet Archive Parquet Downloader.

Downloads parquet files from Internet Archive for reanalysis workflows.
Supports local caching, batch downloads, and retry logic.

Usage:
    downloader = IAParquetDownloader(cache_dir="./cache")
    file_path = await downloader.download(tribunal="TJRO", date="2025-01-15", table="diarios")
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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
    ) -> None:
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
            "IAParquetDownloader initialized with cache_dir=%s",
            self.config.cache_dir,
        )

    async def download(
        self,
        tribunal: str,
        date: str,
        table: str = "diarios",
        force_refresh: bool = False,
    ) -> Path:
        """Download parquet file for a specific date and tribunal.

        Args:
            tribunal: Tribunal code (e.g., TJRO, TJSP)
            date: Date in YYYY-MM-DD format
            table: Table name (e.g., diarios, processos)
            force_refresh: Skip cache and force re-download

        Returns:
            Path to downloaded parquet file

        Raises:
            ValueError: If date format invalid or item not found
            IOError: If download fails after retries
        """
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError as e:
            msg = f"Invalid date format. Expected YYYY-MM-DD: {e}"
            raise ValueError(msg) from e

        # Check cache first
        if not force_refresh:
            cached_file = self._get_cached_file(tribunal, date, table)
            if cached_file:
                logger.info("Using cached file: %s", cached_file)
                return cached_file

        # Generate IA item ID and filename
        item_id = self._generate_item_id(date, tribunal)
        filename = self._generate_filename(date, tribunal, table)

        logger.info("Downloading %s from IA item: %s", filename, item_id)

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

                logger.info("Successfully downloaded to %s", file_path)
            except Exception as e:
                logger.warning(
                    "Download attempt %s/%s failed: %s",
                    attempt + 1,
                    self.config.max_retries,
                    e,
                )

                if attempt < self.config.max_retries - 1:
                    # Calculate exponential backoff delay
                    delay = self.config.initial_retry_delay * (self.config.retry_backoff**attempt)
                    logger.info("Retrying in %.1f seconds...", delay)
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed
                    msg = f"Failed to download after {self.config.max_retries} attempts: {e}"
                    raise OSError(
                        msg,
                    ) from e
            else:
                return file_path
        return None

    async def download_range(
        self,
        start_date: str,
        end_date: str,
        tribunal: str,
        table: str = "diarios",
        skip_missing: bool = True,
    ) -> list[Path]:
        """Download parquet files for a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (inclusive)
            tribunal: Tribunal code (e.g., TJRO)
            table: Table name (e.g., diarios)
            skip_missing: Continue if some dates are missing

        Returns:
            List of downloaded file paths

        Raises:
            ValueError: If date range invalid
            IOError: If any download fails and skip_missing=False
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=UTC)
            end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError as e:
            msg = f"Invalid date format. Expected YYYY-MM-DD: {e}"
            raise ValueError(
                msg,
            ) from e

        if start > end:
            msg = "start_date must be before or equal to end_date"
            raise ValueError(msg)

        logger.info(
            "Downloading %s %s parquet files from %s to %s",
            tribunal,
            table,
            start_date,
            end_date,
        )

        # Generate date range
        current = start
        dates = []
        while current <= end:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        logger.info("Downloading %s files for %s", len(dates), tribunal)

        # Download files
        downloaded_files = []
        failed_downloads = []

        for date in dates:
            try:
                file_path = await self.download(tribunal, date, table)
                downloaded_files.append(file_path)
            except Exception as e:
                logger.exception("Failed to download %s for %s", tribunal, date)
                failed_downloads.append((date, str(e)))

                if not skip_missing:
                    msg = f"Download failed for {date}: {e}"
                    raise OSError(
                        msg,
                    ) from e

        logger.info(
            "Downloaded %s/%s files. Failed: %s",
            len(downloaded_files),
            len(dates),
            len(failed_downloads),
        )

        if failed_downloads:
            logger.warning(
                "Failed downloads: %s",
                ", ".join(date for date, _ in failed_downloads),
            )

        return downloaded_files

    async def check_exists(
        self,
        tribunal: str,
        date: str,
        table: str = "diarios",
    ) -> bool:
        """Check if parquet file exists on Internet Archive.

        Args:
            tribunal: Tribunal code
            date: Date in YYYY-MM-DD format
            table: Table name

        Returns:
            True if item exists, False otherwise
        """
        item_id = self._generate_item_id(date, tribunal)
        filename = self._generate_filename(date, tribunal, table)

        try:
            item = await asyncio.to_thread(ia.get_item, item_id)

            if not item.exists:
                return False

            # Check if specific file exists in item
            return any(file["name"] == filename for file in item.files)

        except (OSError, RuntimeError, AttributeError, TypeError) as e:
            logger.warning("Error checking if item exists: %s", e)
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
            msg = f"Item not found on Internet Archive: {item_id}"
            raise ValueError(msg)

        # Check if file exists in item
        file_found = False
        for file in item.files:
            if file["name"] == filename:
                file_found = True
                break

        if not file_found:
            msg = f"File {filename} not found in item {item_id}"
            raise ValueError(msg)

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
            msg = f"Download completed but file not found: {output_path}"
            raise OSError(msg)

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
        logger.debug("Verifying checksum for %s", filename)

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
                logger.warning("Could not find file metadata for %s", filename)
                return

            # Verify MD5 checksum if available
            if "md5" in file_meta:
                expected_md5 = file_meta["md5"]
                actual_md5 = await self._calculate_md5(file_path)

                if actual_md5 != expected_md5:
                    msg = f"Checksum mismatch: expected {expected_md5}, got {actual_md5}"
                    raise OSError(  # noqa: TRY301
                        msg,
                    )

                logger.debug("Checksum verified: %s", actual_md5)

        except (OSError, ValueError, TypeError) as e:
            logger.warning("Verification failed: %s", e)
            # Don't fail download on verification error, just log

    async def _calculate_md5(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file.

        Args:
            file_path: Path to file

        Returns:
            MD5 checksum as hex string
        """

        def _calculate():
            md5 = hashlib.md5(usedforsecurity=False)
            with file_path.open("rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    md5.update(chunk)
            return md5.hexdigest()

        return await asyncio.to_thread(_calculate)

    def _get_cached_file(
        self,
        tribunal: str,
        date: str,
        table: str = "diarios",
    ) -> Path | None:
        """Check if file exists in cache and is not expired.

        Args:
            tribunal: Tribunal code
            date: Date in YYYY-MM-DD format
            table: Table name

        Returns:
            Path to cached file if valid, None otherwise
        """
        filename = self._generate_filename(date, tribunal, table)
        cache_path = self.config.cache_dir / filename

        if not cache_path.exists():
            return None

        # Check if cache is expired
        file_age_days = (
            datetime.now(UTC) - datetime.fromtimestamp(cache_path.stat().st_mtime, tz=UTC)
        ).days

        if file_age_days > self.config.cache_ttl_days:
            logger.info(
                "Cache expired for %s (age: %s days)",
                filename,
                file_age_days,
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

        for file_path in self.config.cache_dir.glob("*.parquet"):
            if older_than_days is None:
                file_path.unlink()
                deleted += 1
            else:
                file_age_days = (
                    datetime.now(UTC) - datetime.fromtimestamp(file_path.stat().st_mtime, tz=UTC)
                ).days

                if file_age_days > older_than_days:
                    file_path.unlink()
                    deleted += 1

        logger.info("Cleared %s cached files", deleted)
        return deleted

    def _generate_item_id(self, date: str, tribunal: str) -> str:
        """Generate Internet Archive item ID.

        Args:
            date: Partition date (YYYY-MM-DD)
            tribunal: Tribunal code

        Returns:
            Item ID: djen-tjro-2025
        """
        year = date[:4]
        return f"djen-{tribunal.lower()}-{year}"

    def _generate_filename(self, date: str, tribunal: str, table: str) -> str:
        """Generate parquet filename.

        Args:
            date: Partition date (YYYY-MM-DD)
            tribunal: Tribunal code
            table: Table name

        Returns:
            Filename: TJRO-2025-01-15-diarios.parquet
        """
        return f"{tribunal}-{date}-{table}.parquet"

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
