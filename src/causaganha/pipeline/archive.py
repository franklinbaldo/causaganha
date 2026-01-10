"""Archive pipeline for downloading and uploading judicial documents."""

from pathlib import Path
from typing import Any

import structlog

from causaganha.domain.models import Intimation
from causaganha.infrastructure.archive import ArchiveService
from causaganha.infrastructure.document import DocumentService
from causaganha.infrastructure.preservation import PreservationService
from causaganha.storage.repositories.intimation import IntimationRepository


logger = structlog.get_logger()


async def run_archive(
    repository: IntimationRepository,
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
                intimation_id=intimation.id,
            )
            continue

    logger.info("archive_pipeline_complete")


async def _process_intimation(
    intimation: Intimation,
    preservation_service: PreservationService,
    archive_service: ArchiveService,
    repository: IntimationRepository,
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
    intimation_id = intimation.id
    document_url = intimation.link
    intimation_id_str = str(intimation_id)

    if not document_url:
        logger.warning("no_document_url", intimation_id=intimation_id)
        return

    # Upload to Internet Archive
    tribunal = intimation.sigla_tribunal.lower() if intimation.sigla_tribunal else "unknown"
    item_id = f"causaganha-{tribunal}-{intimation_id_str}"

    # Generate metadata from intimation data (refactored)
    # Note: archive_service.generate_metadata expects a dict.
    # We should eventually update ArchiveService to accept Intimation,
    # but for now we convert to dict to maintain compatibility if we don't want to change service signature yet.
    # However, Step 2 is about standardizing repositories.
    # It is cleaner to update ArchiveService.generate_metadata signature or convert here.
    # I will convert here for now to minimize ripple effect, as ArchiveService is in the next step to be moved.
    # Wait, ArchiveService is a Protocol in services/archive.py, but implemented there too.
    # I should pass a dict for now.
    intimation_dict = intimation.model_dump()
    metadata = archive_service.generate_metadata(intimation_dict)

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
