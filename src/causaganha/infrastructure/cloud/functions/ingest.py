import base64
import json
from pathlib import Path
from typing import Any

import structlog
from google.cloud import pubsub_v1

from causaganha.config import settings
from causaganha.infrastructure.clients.archive import InternetArchiveService, LocalArchiveService
from causaganha.infrastructure.clients.document import DocumentService
from causaganha.infrastructure.clients.preservation import PreservationService
from causaganha.infrastructure.cloud.db import (
    COLLECTION_NAME,
    acquire_lock,
    get_firestore_client,
)


logger = structlog.get_logger()


async def ingest_worker(event: dict, context: Any) -> None:
    """Pub/Sub trigger.
    Downloads PDF and uploads to Internet Archive.
    """
    if "data" in event:
        message_data = base64.b64decode(event["data"]).decode("utf-8")
        message = json.loads(message_data)
    else:
        logger.error("no_data_in_event")
        return

    doc_key = message.get("docKey")
    if not doc_key:
        logger.error("missing_doc_key")
        return

    logger.info("ingest_worker_start", doc_key=doc_key)

    db = get_firestore_client()
    publisher = pubsub_v1.PublisherClient()

    # 1. Acquire Lock
    if not await acquire_lock(db, doc_key, "ingest"):
        logger.info("lock_acquisition_failed_or_locked", doc_key=doc_key)
        return

    doc_ref = db.collection(COLLECTION_NAME).document(doc_key)
    doc_snap = await doc_ref.get()
    if not doc_snap.exists:
        logger.error("doc_not_found", doc_key=doc_key)
        return

    data = doc_snap.to_dict()
    pdf_url = data["pdf_url"]

    # Check if already done (Idempotency)
    if data.get("status") in ["pdf_uploaded", "llm_submitted", "llm_done"]:
        logger.info("already_uploaded_skipping", doc_key=doc_key)
        # Emit next stage just in case
        _publish_next_stage(publisher, doc_key)
        return

    try:
        doc_service = DocumentService()

        # Determine Archive Service (Local or IA)
        # For cloud, we prefer IA if keys are present
        if settings.IA_ACCESS_KEY:
            archive_service = InternetArchiveService()
        else:
            # Fallback or error? For "Cloud Functions only" usually we want real IA.
            # But to keep it working if keys missing, we warn.
            logger.warning("no_ia_keys_using_local_mock")
            archive_service = LocalArchiveService(archive_root=Path("/tmp/archive"))

        preservation_service = PreservationService(doc_service, archive_service)

        ia_identifier = f"causaganha-{doc_key[:16]}"
        metadata = {"url": pdf_url, "docKey": doc_key}

        result_url = await preservation_service.preserve_document(
            pdf_url,
            ia_identifier,
            metadata,
        )

        if not result_url:
            msg = "IA upload failed"
            raise RuntimeError(msg)

        # 4. Update status
        from google.cloud import firestore

        await doc_ref.update(
            {
                "status": "pdf_uploaded",
                "ia_identifier": ia_identifier,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
        )

        # 5. Emit next stage
        _publish_next_stage(publisher, doc_key)

    except Exception as e:
        logger.exception("ingest_worker_failed", doc_key=doc_key, error=str(e))
        # Here we could NACK (raise) to retry via Pub/Sub
        raise


def _publish_next_stage(publisher, doc_key) -> None:
    message_json = json.dumps(
        {
            "docKey": doc_key,
            "stage": "llm",
            "force": False,
        },
    ).encode("utf-8")
    publisher.publish(settings.TOPIC_LLM, message_json)
