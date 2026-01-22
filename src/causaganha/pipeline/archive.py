"""Archive pipeline."""

from typing import Any

import structlog

from causaganha.clients.archive import ArchiveService
from causaganha.clients.document import DocumentService
from causaganha.clients.preservation import PreservationService
from causaganha.storage.connection import get_connection
from causaganha.storage.queries import (
    get_unarchived_intimations,
    mark_as_archived,
)


logger = structlog.get_logger()


async def archive_documents(
    doc_service: DocumentService,
    archive_service: ArchiveService,
    limit: int = 10,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Archive intimation documents to Internet Archive.

    Args:
        doc_service: Service to download documents.
        archive_service: Service to upload/archive.
        limit: Max number of items to process.
        dry_run: If True, do not upload.

    Returns:
        Statistics dictionary.
    """
    logger.info("archive_start", limit=limit, dry_run=dry_run)

    con = get_connection()
    preservation_service = PreservationService(doc_service, archive_service)

    processed = 0
    archived = 0
    failed = 0

    try:
        intimations = get_unarchived_intimations(con, limit=limit)

        if not intimations:
            logger.info("no_intimations_to_archive")
            return {
                "processed": 0,
                "archived": 0,
                "failed": 0,
                "status": "success",
            }

        for intimation in intimations:
            processed += 1
            intimation_id = intimation["id"]
            document_url = intimation["link"]

            try:
                # Generate item ID
                tribunal = intimation.get("sigla_tribunal", "unknown").lower()
                item_id = f"causaganha-{tribunal}-{intimation_id}"

                # Generate metadata
                metadata = archive_service.generate_metadata(intimation)

                # Preserve
                ia_url = await preservation_service.preserve_document(
                    document_url,
                    item_id,
                    metadata,
                    dry_run,
                )

                if ia_url:
                    mark_as_archived(con, intimation_id, ia_url)
                    archived += 1
                    logger.info("archived_success", id=intimation_id, url=ia_url)
                elif dry_run:
                    logger.info("dry_run_archived", id=intimation_id)
                else:
                    logger.warning("archive_failed_no_url", id=intimation_id)
                    failed += 1

            except Exception as e:
                logger.exception("archive_item_failed", id=intimation_id, error=str(e))
                failed += 1

        logger.info(
            "archive_complete",
            processed=processed,
            archived=archived,
            failed=failed,
        )

        return {
            "processed": processed,
            "archived": archived,
            "failed": failed,
            "status": "success",
        }

    except Exception as e:
        logger.exception("archive_pipeline_failed", error=str(e))
        return {
            "processed": processed,
            "archived": archived,
            "failed": failed,
            "status": "failed",
            "error": str(e),
        }
