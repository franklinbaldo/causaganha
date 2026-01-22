"""Preservation service for long-term document archiving."""

from pathlib import Path

import structlog

from causaganha.infrastructure.clients.archive import ArchiveService
from causaganha.infrastructure.clients.document import DocumentService


logger = structlog.get_logger()


class PreservationService:
    """Service to coordinate document preservation."""

    def __init__(
        self,
        doc_service: DocumentService,
        archive_service: ArchiveService,
    ) -> None:
        """Initialize the service.

        Args:
            doc_service: Service to download documents.
            archive_service: Service to upload documents.
        """
        self.doc_service = doc_service
        self.archive_service = archive_service

    async def preserve_document(
        self,
        document_url: str,
        item_id: str,
        metadata: dict,
        dry_run: bool = False,
    ) -> str | None:
        """Download and archive a document.

        Args:
            document_url: The URL of the document to download.
            item_id: The target ID for the archive.
            metadata: Metadata to attach to the archive item.
            dry_run: If True, do not perform the upload.

        Returns:
            The URL of the archived item if successful, None otherwise.
        """
        logger.info("preserving_document", url=document_url, item_id=item_id)

        # Download
        content = await self.doc_service.download_pdf(document_url)
        if not content:
            logger.error("download_failed", url=document_url)
            return None

        # Create temp file
        temp_dir = Path("data/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        # Use a safe filename based on item_id hash or similar to avoid path issues,
        # but here we can just use a generic name since we control the dir.
        # Actually, ArchiveService might use the filename in the upload.
        filename = "document.pdf"
        temp_path = temp_dir / f"{item_id}_{filename}"

        try:
            temp_path.write_bytes(content)

            if dry_run:
                logger.info("dry_run_skipping_upload", item_id=item_id)
                return None

            # Upload
            ia_url = await self.archive_service.upload_file(temp_path, item_id, metadata)
            return ia_url

        except Exception as e:
            logger.exception("preservation_failed", item_id=item_id, error=str(e))
            return None

        finally:
            if temp_path.exists():
                temp_path.unlink()
