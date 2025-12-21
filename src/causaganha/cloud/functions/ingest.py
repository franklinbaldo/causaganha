import base64
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import structlog
from google.cloud import pubsub_v1

from causaganha.cloud.db import (
    COLLECTION_NAME,
    acquire_lock,
    get_firestore_client,
)
from causaganha.services.archive import InternetArchiveService, LocalArchiveService
from causaganha.services.document import DocumentService


logger = structlog.get_logger()

# Config
TOPIC_LLM = os.getenv("TOPIC_LLM", "projects/my-project/topics/llm")


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
        # Should we NACK? If we NACK, it retries immediately.
        # Better to let it ack and rely on next run or retry dispatcher if we strictly follow "Function A/B" split without Tasks.
        # But Pub/Sub standard pattern is NACK if transient. Locking implies another worker is busy.
        # We'll simple return (Ack) to avoid hot loop on locked item.
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
        # 2. Download PDF
        doc_service = DocumentService()
        pdf_bytes = await doc_service.download_pdf(pdf_url)

        if not pdf_bytes:
            raise RuntimeError(f"Failed to download PDF from {pdf_url}")

        # 3. Upload to IA
        # Using temp file as IA service expects path
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = Path(tmp.name)

        # Rename to document.pdf for upload consistency if the service uses the filename
        # Ideally we pass a target filename to upload_file, but based on existing service it takes file_path.
        # We can rename the temp file to 'document.pdf' in a temp dir.

        upload_path = tmp_path.parent / "document.pdf"
        # If multiple concurrent runs, this name collision in /tmp/ is risky.
        # Use a unique temp dir.

        with tempfile.TemporaryDirectory() as tmp_dir:
            upload_path = Path(tmp_dir) / "document.pdf"
            with open(upload_path, "wb") as f:
                f.write(pdf_bytes)

            try:
                # Determine Archive Service (Local or IA)
                # For cloud, we prefer IA if keys are present
                if os.getenv("IA_ACCESS_KEY"):
                    archive_service = InternetArchiveService()
                else:
                    # Fallback or error? For "Cloud Functions only" usually we want real IA.
                    # But to keep it working if keys missing, we warn.
                    logger.warning("no_ia_keys_using_local_mock")
                    archive_service = LocalArchiveService(archive_root=Path("/tmp/archive"))

                ia_identifier = f"causaganha-{doc_key[:16]}"

                # Check if exists first? Plan says "Ensure... stored".
                # IA Service `upload_file` handles some of this, but we can check.

                result_url = await archive_service.upload_file(
                    file_path=upload_path,
                    item_id=ia_identifier,
                    metadata={"url": pdf_url, "docKey": doc_key},
                )

                if not result_url:
                    raise RuntimeError("IA upload failed")
            finally:
                pass

        # Cleanup original tmp if we didn't use the with block fully for it (we did)
        if tmp_path.exists():
            os.unlink(tmp_path)

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
        raise e


def _publish_next_stage(publisher, doc_key):
    message_json = json.dumps({"docKey": doc_key, "stage": "llm", "force": False}).encode("utf-8")
    publisher.publish(TOPIC_LLM, message_json)
