"""Archive pipeline for downloading and uploading judicial documents."""

import asyncio
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import structlog

from causaganha.services.archive import InternetArchiveService
from causaganha.services.document import DocumentService
from causaganha.storage.repository import IntimationRepository

logger = structlog.get_logger()


async def run_archive(
    repository: IntimationRepository,
    doc_service: DocumentService,
    ia_service: InternetArchiveService,
    limit: int = 10,
    dry_run: bool = False,
) -> None:
    """Run the archive pipeline.

    Downloads intimation documents and uploads them to Internet Archive.

    Args:
        repository: Repository for accessing intimations.
        doc_service: Service for downloading documents.
        ia_service: Service for uploading to Internet Archive.
        limit: Maximum number of documents to process.
        dry_run: If True, don't actually upload to IA.
    """
    logger.info(
        "starting_archive_pipeline", limit=limit, dry_run=dry_run
    )

    # Get unarchived intimations
    intimations = await repository.get_unarchived_intimations(limit=limit)

    if not intimations:
        logger.info("no_intimations_to_archive")
        return

    logger.info("processing_intimations", count=len(intimations))

    for intimation in intimations:
        try:
            await _process_intimation(
                intimation, doc_service, ia_service, repository, dry_run
            )
        except Exception:
            logger.exception(
                "intimation_processing_failed",
                intimation_id=intimation.get("id"),
            )
            continue

    logger.info("archive_pipeline_complete")


async def _process_intimation(
    intimation: dict[str, Any],
    doc_service: DocumentService,
    ia_service: InternetArchiveService,
    repository: IntimationRepository,
    dry_run: bool,
) -> None:
    """Process a single intimation for archiving.

    Args:
        intimation: The intimation data.
        doc_service: Document download service.
        ia_service: Internet Archive upload service.
        repository: Repository for updates.
        dry_run: If True, skip actual upload.
    """
    intimation_id = intimation.get("id")
    document_url = intimation.get("url_documento")

    if not document_url:
        logger.warning("no_document_url", intimation_id=intimation_id)
        return

    logger.info(
        "downloading_document",
        intimation_id=intimation_id,
        url=document_url,
    )

    # Download the document
    content = await doc_service.download_pdf(document_url)
    if not content:
        logger.error("download_failed", intimation_id=intimation_id)
        return

    # Save temporarily
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)

    filename = f"intimation_{intimation_id}.pdf"
    temp_path = temp_dir / filename

    temp_path.write_bytes(content)
    logger.info("document_saved", path=str(temp_path), size=len(content))

    if dry_run:
        logger.info("dry_run_skipping_upload", intimation_id=intimation_id)
        temp_path.unlink()  # Clean up
        return

    # Upload to Internet Archive
    item_id = f"causaganha-tjro-{intimation_id}"

    # Generate metadata from intimation data (refactored)
    metadata = ia_service.generate_metadata(intimation)

    ia_url = await ia_service.upload_file(temp_path, item_id, metadata)

    if ia_url:
        logger.info(
            "upload_success",
            intimation_id=intimation_id,
            ia_url=ia_url,
        )
        # Update repository to mark as archived
        await repository.mark_as_archived(intimation_id, ia_url)
    else:
        logger.error("upload_failed", intimation_id=intimation_id)

    # Clean up temporary file
    if temp_path.exists():
        temp_path.unlink()
