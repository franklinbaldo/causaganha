"""Internet Archive Upload Module.

.. deprecated::
    This module uses the ``internetarchive`` Python library for uploads.
    The production pipeline uses httpx-based uploads via
    ``scripts/pipeline/ia_s3.py`` instead, because the ``internetarchive``
    library (like boto3) does not reliably support the ``x-archive-meta-*``
    headers that IA requires. See CONTRIBUTING.md and PR #348.

    **Do not use this module for production uploads.**
    Use ``scripts.pipeline.ia_s3.upload_to_ia()`` instead.

    This module is retained only for metadata queries, download operations,
    and legacy/experimental upload paths that are not part of the daily
    pipeline.

Uploads Parquet files to Internet Archive for permanent, free storage.
Supports retry logic, metadata generation, and upload verification.

Usage:
    uploader = InternetArchiveUploader()
    ia_url = await uploader.upload_parquet(
        file_path, tribunal="TJRO", partition_date="2025-01-15"
    )
"""

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

import internetarchive as ia
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)


logger = logging.getLogger(__name__)


@dataclass
class IAMetadata:
    """Metadata for Internet Archive item."""

    title: str
    collection: str = "causaganha"
    mediatype: str = "data"
    subject: list[str] = field(default_factory=list)
    description: str = ""
    date: str = ""
    coverage: str = ""
    format: str = "Parquet"
    language: str = "por"
    creator: str = "CausaGanha Project"
    rights: str = "CC0 1.0 Universal (Public Domain)"
    licenseurl: str = "https://creativecommons.org/publicdomain/zero/1.0/"

    def to_dict(self) -> dict:
        """Convert to dictionary for IA API."""
        return {
            "title": self.title,
            "collection": self.collection,
            "mediatype": self.mediatype,
            "subject": self.subject,
            "description": self.description,
            "date": self.date,
            "coverage": self.coverage,
            "format": self.format,
            "language": self.language,
            "creator": self.creator,
            "rights": self.rights,
            "licenseurl": self.licenseurl,
        }


@dataclass
class UploadConfig:
    """Configuration for Internet Archive uploads."""

    max_retries: int = 3
    retry_backoff: float = 2.0  # Exponential backoff multiplier
    initial_retry_delay: float = 2.0  # Seconds
    verify_after_upload: bool = True
    checksum: bool = True  # Enable MD5 checksum verification


class InternetArchiveUploader:
    """Uploads Parquet files to Internet Archive."""

    def __init__(
        self,
        config: UploadConfig | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        """Initialize Internet Archive uploader.

        Args:
            config: Upload configuration (uses defaults if None)
            access_key: IA access key (uses env var if None)
            secret_key: IA secret key (uses env var if None)

        Note:
            Credentials can be configured via:
            - Environment variables: IA_ACCESS_KEY, IA_SECRET_KEY
            - Config file: ~/.config/ia.ini
            - Parameters passed here
        """
        self.config = config or UploadConfig()

        # Configure IA session with credentials if provided
        if access_key and secret_key:
            ia.configure(access_key, secret_key)

        logger.info("InternetArchiveUploader initialized")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(OSError),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def upload_parquet(
        self,
        file_path: Path,
        tribunal: str,
        partition_date: str,
        file_size_mb: float | None = None,
        row_count: int | None = None,
    ) -> str:
        """Upload Parquet file to Internet Archive.

        Args:
            file_path: Path to Parquet file
            tribunal: Tribunal code (e.g., TJRO)
            partition_date: Date in YYYY-MM-DD format
            file_size_mb: File size in MB (calculated if None)
            row_count: Number of rows in file (for metadata)

        Returns:
            Internet Archive item URL

        Raises:
            ValueError: If file doesn't exist
            IOError: If upload fails after retries
        """
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise ValueError(msg)

        # Generate item ID and metadata
        item_id = self._generate_item_id(partition_date, tribunal)
        metadata = self._generate_metadata(
            tribunal,
            partition_date,
            file_size_mb,
            row_count,
        )

        logger.info(f"Uploading {file_path.name} to IA item: {item_id}")

        # Run blocking IA upload in thread pool
        await asyncio.to_thread(
            self._upload_file,
            item_id,
            file_path,
            metadata,
        )

        # Verify upload if configured
        if self.config.verify_after_upload:
            await self._verify_upload(item_id, file_path.name)

        ia_url = f"https://archive.org/details/{item_id}"
        logger.info(f"Successfully uploaded to {ia_url}")
        return ia_url

    def _upload_file(
        self,
        item_id: str,
        file_path: Path,
        metadata: IAMetadata,
    ) -> None:
        """Upload file to Internet Archive (blocking call).

        Args:
            item_id: IA item identifier
            file_path: Path to file to upload
            metadata: IA metadata object

        Raises:
            Exception: If upload fails
        """
        # Get or create IA item
        item = ia.get_item(item_id)

        # Get file size for Content-Length header (fix for HTTP 411)
        file_size = file_path.stat().st_size

        # Open file and upload with explicit Content-Length
        with file_path.open("rb") as f:
            response = item.upload(
                {file_path.name: f},
                metadata=metadata.to_dict(),
                checksum=self.config.checksum,
                verify=True,
                queue_derive=True,  # Generate derivatives (thumbnails, etc.)
                verbose=False,
                headers={"Content-Length": str(file_size)},
            )

        # Check response
        if response[0].status_code != 200:
            msg = f"Upload failed with status {response[0].status_code}: {response[0].text}"
            raise OSError(
                msg,
            )

    async def _verify_upload(self, item_id: str, filename: str) -> None:
        """Verify file was uploaded successfully.

        Args:
            item_id: IA item identifier
            filename: Filename to verify

        Raises:
            IOError: If verification fails
        """
        logger.debug(f"Verifying upload for {item_id}/{filename}")

        # Get item metadata
        item = await asyncio.to_thread(ia.get_item, item_id)

        # Check if file exists in item
        file_found = False
        for file in item.files:
            if file["name"] == filename:
                file_found = True
                logger.debug(f"Verified file exists: {filename}")
                break

        if not file_found:
            msg = f"Verification failed: File {filename} not found in item {item_id}"
            raise OSError(
                msg,
            )

    def _generate_item_id(self, date: str, tribunal: str) -> str:
        """Generate Internet Archive item ID.

        .. note::
            This generates ``djen-raw-{date}-{tribunal}`` which differs from
            the production item ID scheme ``djen-{date}`` used by
            ``scripts/pipeline/ia_s3.py`` and ``scripts/pipeline/collect.py``.
            This module is NOT used for production uploads.

        Args:
            date: Partition date (YYYY-MM-DD)
            tribunal: Tribunal code

        Returns:
            Item ID: djen-raw-2025-01-15-TJRO
        """
        return f"djen-raw-{date}-{tribunal}"

    def _generate_metadata(
        self,
        tribunal: str,
        date: str,
        file_size_mb: float | None = None,
        row_count: int | None = None,
    ) -> IAMetadata:
        """Generate metadata for Internet Archive item.

        Args:
            tribunal: Tribunal code (e.g., TJRO)
            date: Partition date (YYYY-MM-DD)
            file_size_mb: File size in MB (optional)
            row_count: Number of rows (optional)

        Returns:
            IAMetadata object
        """
        # Tribunal full names
        tribunal_names = {
            "TJRO": "Tribunal de Justiça de Rondônia",
            "TJAC": "Tribunal de Justiça do Acre",
            "TJSP": "Tribunal de Justiça de São Paulo",
            "TJRJ": "Tribunal de Justiça do Rio de Janeiro",
            "TJMG": "Tribunal de Justiça de Minas Gerais",
            # Add more as needed
        }

        tribunal_full = tribunal_names.get(tribunal, f"Tribunal {tribunal}")

        # Build description
        description_parts = [
            f"Daily judicial decision data from {tribunal_full} for {date}.",
            "Contains lawyer information, case outcomes, and LLM-extracted decision analysis.",
        ]

        if row_count:
            description_parts.append(f"Total decisions: {row_count:,}")

        if file_size_mb:
            description_parts.append(f"File size: {file_size_mb:.2f} MB")

        description = " ".join(description_parts)

        return IAMetadata(
            title=f"CausaGanha - {tribunal} - {date}",
            subject=[
                "judicial decisions",
                "brazil",
                tribunal,
                date,
                "legal data",
                "open data",
            ],
            description=description,
            date=date,
            coverage=f"{tribunal} ({tribunal_full})",
        )

    async def check_if_exists(self, tribunal: str, partition_date: str) -> bool:
        """Check if item already exists on Internet Archive.

        Args:
            tribunal: Tribunal code
            partition_date: Date in YYYY-MM-DD format

        Returns:
            True if item exists, False otherwise
        """
        item_id = self._generate_item_id(partition_date, tribunal)

        try:
            item = await asyncio.to_thread(ia.get_item, item_id)
            return item.exists
        except Exception as e:
            logger.warning(f"Error checking if item exists: {e}")
            return False

    async def get_item_url(self, tribunal: str, partition_date: str) -> str:
        """Get Internet Archive URL for an item.

        Args:
            tribunal: Tribunal code
            partition_date: Date in YYYY-MM-DD format

        Returns:
            IA item URL
        """
        item_id = self._generate_item_id(partition_date, tribunal)
        return f"https://archive.org/details/{item_id}"
