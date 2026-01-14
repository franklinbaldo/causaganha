"""Archive pipeline for downloading and uploading judicial documents."""

from pathlib import Path
from typing import Any

import structlog

from causaganha.domain.interfaces import IntimationRepositoryProtocol
from causaganha.infrastructure.clients.archive import ArchiveService
from causaganha.infrastructure.clients.document import DocumentService
from causaganha.infrastructure.clients.preservation import PreservationService


logger = structlog.get_logger()


async def run_archive(
    repository: IntimationRepositoryProtocol,
    doc_service: DocumentService,
    archive_service: ArchiveService,
    limit: int = 10,
    dry_run: bool = False,
) -> None:
    """Run the archive pipeline.

    Downloads intimation documents and uploads them to Internet Archive.

    Args:
        repository: Repository for accessing intimations.
        doc_service: Service for downloading documents.
        archive_service: Service for uploading/archiving PDFs.
        limit: Maximum number of documents to process.
        dry_run: If True, don't actually upload to IA.
    """
    logger.info(
        "starting_archive_pipeline", limit=limit, dry_run=dry_run,
    )

    # Get unarchived intimations
    intimations = await repository.get_unarchived_intimations(limit=limit)

    if not intimations:
        logger.info("no_intimations_to_archive")
        return

    logger.info("processing_intimations", count=len(intimations))

    preservation_service = PreservationService(doc_service, archive_service)

    for intimation in intimations:
        try:
            await _process_intimation(
                intimation, preservation_service, archive_service, repository, dry_run,
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
    preservation_service: PreservationService,
    archive_service: ArchiveService,
    repository: IntimationRepositoryProtocol,
    dry_run: bool,
) -> None:
    """Process a single intimation for archiving.

    Args:
        intimation: The intimation data.
        preservation_service: Preservation service.
        archive_service: Archive service (for metadata generation).
        repository: Repository for updates.
        dry_run: If True, skip actual upload.
    """
    intimation_id = intimation.get("id")
    document_url = intimation.get("link")
    intimation_id_str = str(intimation_id)

    if not document_url:
        logger.warning("no_document_url", intimation_id=intimation_id)
        return

    # Upload to Internet Archive
    tribunal = intimation.get("sigla_tribunal", "unknown").lower()
    item_id = f"causaganha-{tribunal}-{intimation_id_str}"

    # Generate metadata from intimation data (refactored)
    metadata = archive_service.generate_metadata(intimation)

    ia_url = await preservation_service.preserve_document(
        document_url, item_id, metadata, dry_run,
    )

    if ia_url:
        logger.info(
            "upload_success",
            intimation_id=intimation_id,
            ia_url=ia_url,
        )
        await repository.mark_as_archived(intimation_id_str, ia_url)
    elif not dry_run:
        logger.error("upload_failed", intimation_id=intimation_id)
