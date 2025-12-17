"""Internet Archive service for uploading documents."""

import asyncio
import os
import shutil
from datetime import date
from pathlib import Path
from typing import Any
from typing import Protocol

import internetarchive as ia
import structlog

from causaganha.config import DATA_DIR
from causaganha.services.constants import (
    IA_DEFAULT_COLLECTION,
    IA_DEFAULT_CREATOR,
    IA_DEFAULT_MEDIATYPE,
    IA_DEFAULT_SUBJECTS,
    DEFAULT_UPLOAD_RETRIES,
    DEFAULT_RETRY_SLEEP_SECONDS,
    DEFAULT_UPLOAD_TIMEOUT_SECONDS,
)

logger = structlog.get_logger()


class ArchiveService(Protocol):
    """Abstract interface for archiving PDFs (Internet Archive or local fallback)."""

    async def upload_file(
        self,
        file_path: Path,
        item_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> str | None: ...

    async def check_item_exists(self, item_id: str) -> bool: ...

    def generate_metadata(self, intimation_data: dict[str, Any]) -> dict[str, Any]: ...


class LocalArchiveService:
    """Local filesystem archive fallback (no API keys required)."""

    def __init__(self, archive_root: Path | None = None):
        self.archive_root = archive_root or (DATA_DIR / "pdf_archive")
        self.archive_root.mkdir(parents=True, exist_ok=True)

    async def upload_file(
        self,
        file_path: Path,
        item_id: str,
        metadata: dict[str, Any] | None = None,  # metadata is ignored for local storage
    ) -> str | None:
        if not file_path.exists():
            logger.error("file_not_found", path=str(file_path))
            return None

        dest_dir = self.archive_root / item_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / file_path.name

        await asyncio.to_thread(shutil.copy2, file_path, dest_path)
        logger.info("local_archive_saved", item_id=item_id, path=str(dest_path))
        return str(dest_path)

    async def check_item_exists(self, item_id: str) -> bool:
        return (self.archive_root / item_id).exists()

    def generate_metadata(self, intimation_data: dict[str, Any]) -> dict[str, Any]:
        return {}


def create_archive_service() -> ArchiveService:
    """Create the best available archive service based on environment configuration."""
    access_key = os.getenv("IA_ACCESS_KEY")
    secret_key = os.getenv("IA_SECRET_KEY")
    if access_key and secret_key:
        return InternetArchiveService()
    return LocalArchiveService()


class InternetArchiveService:
    """Service for uploading documents to Internet Archive."""

    def __init__(self, upload_settings: dict[str, Any] | None = None):
        """Initialize the Internet Archive service.

        Args:
            upload_settings: Optional custom upload settings (retries, timeout, etc.).
        """
        self.session = ia.get_session()
        self.upload_settings = upload_settings or {
            "retries": DEFAULT_UPLOAD_RETRIES,
            "retries_sleep": DEFAULT_RETRY_SLEEP_SECONDS,
            "timeout": DEFAULT_UPLOAD_TIMEOUT_SECONDS,
        }

    async def upload_file(
        self,
        file_path: Path,
        item_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """Upload a file to Internet Archive with retry logic.

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

        logger.info("upload_starting", item_id=item_id, file=file_path.name)

        # Retry logic (TDD-driven improvement)
        max_retries = self.upload_settings.get("retries", 3)
        retry_sleep = self.upload_settings.get("retries_sleep", 5)

        for attempt in range(max_retries):
            try:
                logger.debug("upload_attempt", attempt=attempt + 1, max_retries=max_retries)

                # Run the blocking IA upload in a thread pool
                result = await asyncio.to_thread(
                    self._sync_upload, file_path, item_id, metadata or {}
                )

                logger.info("upload_success", item_id=item_id, url=result)
                return result

            except (ConnectionError, TimeoutError) as e:
                # Transient errors - retry
                if attempt < max_retries - 1:
                    logger.warning(
                        "upload_retry",
                        attempt=attempt + 1,
                        error=str(e),
                        retry_in=retry_sleep,
                    )
                    await asyncio.sleep(retry_sleep)
                else:
                    logger.error("upload_failed_max_retries", item_id=item_id, error=str(e))
                    return None

            except Exception as e:
                # Non-transient errors - don't retry
                logger.exception("upload_failed", item_id=item_id, path=str(file_path), error=str(e))
                return None

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

    def generate_metadata(self, intimation_data: dict[str, Any]) -> dict[str, Any]:
        """Generate Internet Archive metadata from intimation data.

        Args:
            intimation_data: Intimation data dictionary.

        Returns:
            Formatted metadata dict for IA upload.
        """
        processo = intimation_data.get("numero_processo", "unknown")
        tribunal = intimation_data.get("sigla_tribunal", "unknown")
        data_pub = intimation_data.get("data_disponibilizacao", date.today().isoformat())

        metadata = {
            "collection": IA_DEFAULT_COLLECTION,
            "mediatype": IA_DEFAULT_MEDIATYPE,
            "title": f"{tribunal} - Processo {processo}",
            "creator": IA_DEFAULT_CREATOR,
            "subject": IA_DEFAULT_SUBJECTS + [tribunal.lower()],
            "description": f"Intimação judicial do processo {processo}",
            "date": data_pub,
        }

        return metadata
