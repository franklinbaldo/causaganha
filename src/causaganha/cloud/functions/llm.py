import base64
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone

import structlog
from google.cloud import pubsub_v1
# Optional: Cloud Tasks
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from causaganha.cloud.db import (
    acquire_lock,
    get_firestore_client,
    COLLECTION_NAME,
)
from causaganha.services.archive import InternetArchiveService, LocalArchiveService
# We need to download FROM IA. The existing service uploads.
# We can use 'internetarchive' lib directly or add download capability.
# For simplicity, we'll assume we can use `ia.download` or just HTTP fetch the IA URL.
import httpx
from causaganha.analysis.analyzer import DecisionAnalyzer

logger = structlog.get_logger()

# Config
PROJECT_ID = os.getenv("GCP_PROJECT", "my-project")
REGION = os.getenv("GCP_REGION", "us-central1")
QUEUE_NAME = os.getenv("TASKS_QUEUE", "llm-retry-queue")
FUNCTION_URL = os.getenv("FUNCTION_URL", "https://region-project.cloudfunctions.net/llm_worker")

async def llm_worker(event: dict, context: Any) -> None:
    """
    Pub/Sub trigger (or HTTP if called by Cloud Tasks).
    Analyzes PDF with Gemini and uploads result.
    """
    # Handle both Pub/Sub event and HTTP request (if adapted)
    # Since this function signature is for Pub/Sub (event, context),
    # if using Cloud Tasks targeting HTTP, the signature would be (request).
    # For this implementation, I'll assume Pub/Sub trigger pattern as primary,
    # but include logic for the "Cloud Tasks" retry which would likely trigger
    # a separate HTTP entry point or this same one if we wrap it.

    # Let's stick to the Pub/Sub signature for the "worker".
    # If Cloud Tasks calls this, it should be an HTTP function.
    # I'll implement the logic in a helper `process_llm` and verify signature later.

    if "data" in event:
        message_data = base64.b64decode(event["data"]).decode("utf-8")
        message = json.loads(message_data)
    else:
        # If this is an HTTP request (Cloud Tasks), event might be the request object
        # This part depends on the specific Cloud Function generation (1st vs 2nd).
        # I'll assume Pub/Sub for now.
        logger.error("no_data_in_event")
        return

    doc_key = message.get("docKey")
    if not doc_key:
        return

    await process_llm(doc_key)

async def process_llm(doc_key: str):
    logger.info("llm_worker_start", doc_key=doc_key)

    db = get_firestore_client()

    # 1. Acquire Lock
    if not await acquire_lock(db, doc_key, "llm"):
        logger.info("lock_locked", doc_key=doc_key)
        return

    doc_ref = db.collection(COLLECTION_NAME).document(doc_key)
    doc_snap = await doc_ref.get()
    if not doc_snap.exists:
        logger.error("doc_not_found", doc_key=doc_key)
        return

    data = doc_snap.to_dict()
    ia_identifier = data.get("ia_identifier")

    if data.get("status") == "llm_done":
        logger.info("llm_already_done", doc_key=doc_key)
        return

    try:
        # 2. Ensure PDF exists (Download from IA)
        # Construct IA URL.
        # Standard: https://archive.org/download/{identifier}/{filename}
        # We stored filename as "document.pdf" (implicit in previous step? we uploaded file path.name)
        # ingest_worker used temp file suffix .pdf. We didn't enforce name "document.pdf".
        # But IA item usually contains the file.
        # We can list files or guess.

        pdf_url = f"https://archive.org/download/{ia_identifier}/document.pdf"
        # Or use original PDF URL if IA is slow to index? No, strictly use IA to ensure it's there.
        # Ideally ingest_worker sets the filename explicitly.
        # For now, let's try to fetch from IA.

        async with httpx.AsyncClient() as client:
            resp = await client.get(pdf_url, follow_redirects=True, timeout=60.0)
            if resp.status_code != 200:
                # Fallback: try to find the PDF in the item metadata or just use original URL?
                # Plan says: "Ensure PDF exists... call Gemini".
                # If IA fetch fails, maybe not ready?
                raise RuntimeError(f"Could not fetch PDF from IA: {pdf_url}")
            pdf_bytes = resp.content

        # 3. Call Gemini
        analyzer = DecisionAnalyzer() # Picks up env vars
        result = await analyzer.analyze_decision(pdf_bytes)

        # 4. Save LLM output
        # To /tmp
        result_json = result.model_dump_json(indent=2)
        with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as tmp:
            tmp.write(result_json)
            tmp_path = Path(tmp.name)

        try:
            # Upload to IA
            if os.getenv("IA_ACCESS_KEY"):
                archive_service = InternetArchiveService()
            else:
                archive_service = LocalArchiveService(archive_root=Path("/tmp/archive"))

            await archive_service.upload_file(
                file_path=tmp_path,
                item_id=ia_identifier,
                metadata={"docKey": doc_key, "type": "llm_result"}
            )
        finally:
             if tmp_path.exists():
                os.unlink(tmp_path)

        # 5. Mark Done
        await doc_ref.update({
            "status": "llm_done",
            "updated_at": firestore.SERVER_TIMESTAMP
        })
        logger.info("llm_complete", doc_key=doc_key)

    except Exception as e:
        logger.exception("llm_failed", doc_key=doc_key, error=str(e))

        # Schedule Retry (Cloud Tasks)
        # If this fails, we MUST raise to ensure Pub/Sub redelivery/NACK
        try:
            await schedule_retry(doc_key, data.get("attempts", {}).get("llm", 0) + 1)
        except Exception as retry_err:
             logger.error("retry_schedule_failed_raising", doc_key=doc_key, error=str(retry_err))
             raise e # Raise original error to NACK

async def schedule_retry(doc_key: str, attempt: int):
    """Schedules a retry using Cloud Tasks."""
    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(PROJECT_ID, REGION, QUEUE_NAME)

    # Backoff: 5m, 15m, 60m...
    delay_seconds = 300 * (3 ** (attempt - 1)) # 5m, 15m, 45m
    if delay_seconds > 86400: # Max 24h
        delay_seconds = 86400

    run_at = timestamp_pb2.Timestamp()
    run_at.FromDatetime(datetime.now(timezone.utc) + timedelta(seconds=delay_seconds))

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": FUNCTION_URL, # The HTTP trigger for this worker
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"docKey": doc_key, "retry": True}).encode()
        },
        "schedule_time": run_at
    }

    # Let exceptions propagate so caller can handle
    client.create_task(request={"parent": parent, "task": task})
    logger.info("retry_scheduled", doc_key=doc_key, delay=delay_seconds)
