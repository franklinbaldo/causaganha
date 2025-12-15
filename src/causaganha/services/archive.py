"""Internet Archive service for uploading documents."""

import asyncio
from pathlib import Path
from typing import Any

import internetarchive as ia
import structlog

logger = structlog.get_logger()


class InternetArchiveService:
    """Service for uploading documents to Internet Archive."""

    def __init__(self):
        """Initialize the Internet Archive service."""
        self.session = ia.get_session()

    async def upload_file(
        self,
        file_path: Path,
        item_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """Upload a file to Internet Archive.

        Args:
            file_path: Path to the file to upload.
            item_id: Internet Archive item identifier.
            metadata: Optional metadata for the upload.

        Returns:
            The Internet Archive URL if successful, None otherwise.
        """
        if not file_path.exists():
            logger.error("file_not_found", path=str(file_path))
            return None

        try:
            # Run the blocking IA upload in a thread pool
            result = await asyncio.to_thread(
                self._sync_upload, file_path, item_id, metadata or {}
            )
            return result
        except Exception:
            logger.exception("upload_failed", item_id=item_id, path=str(file_path))
            return None

    def _sync_upload(
        self, file_path: Path, item_id: str, metadata: dict[str, Any]
    ) -> str:
        """Synchronous upload to IA.

        Args:
            file_path: Path to the file.
            item_id: IA item identifier.
            metadata: Upload metadata.

        Returns:
            The IA URL.
        """
        logger.info("uploading_to_ia", item_id=item_id, file=file_path.name)

        item = self.session.get_item(item_id)
        result = item.upload_file(
            file_path,
            metadata=metadata,
            verbose=True,
            retries=3,
            retries_sleep=5,
        )

        if result:
            url = f"https://archive.org/details/{item_id}"
            logger.info("upload_success", url=url)
            return url
        else:
            raise RuntimeError(f"Upload failed for {item_id}")

    async def check_item_exists(self, item_id: str) -> bool:
        """Check if an item exists on Internet Archive.

        Args:
            item_id: The IA item identifier.

        Returns:
            True if the item exists, False otherwise.
        """
        try:
            result = await asyncio.to_thread(self._sync_check_item, item_id)
            return result
        except Exception:
            logger.exception("check_failed", item_id=item_id)
            return False

    def _sync_check_item(self, item_id: str) -> bool:
        """Synchronous check for item existence.

        Args:
            item_id: The IA item identifier.

        Returns:
            True if exists, False otherwise.
        """
        item = self.session.get_item(item_id)
        return item.exists
