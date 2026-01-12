import base64
import json
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import structlog

# Optional: Cloud Tasks
from google.cloud import firestore, tasks_v2
from google.protobuf import timestamp_pb2

from causaganha.infrastructure.ai.analyzer import DecisionAnalyzer
from causaganha.infrastructure.cloud.db import (
    COLLECTION_NAME,
    acquire_lock,
    get_firestore_client,
)
from causaganha.infrastructure.clients.archive import InternetArchiveService, LocalArchiveService


logger = structlog.get_logger()

# Config
from causaganha.config import settings


async def schedule_retry(doc_key: str, attempt: int) -> None:
    """Schedules a retry using Cloud Tasks."""
    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(settings.GCP_PROJECT, settings.GCP_REGION, settings.TASKS_QUEUE)

    # Backoff: 5m, 15m, 60m...
    delay_seconds = 300 * (3 ** (attempt - 1)) # 5m, 15m, 45m
    delay_seconds = min(delay_seconds, 86400)

    run_at = timestamp_pb2.Timestamp()
    run_at.FromDatetime(datetime.now(UTC) + timedelta(seconds=delay_seconds))

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": settings.FUNCTION_URL, # The HTTP trigger for this worker
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"docKey": doc_key, "retry": True}).encode(),
        },
        "schedule_time": run_at,
    }

    # Let exceptions propagate so caller can handle
    client.create_task(request={"parent": parent, "task": task})
    logger.info("retry_scheduled", doc_key=doc_key, delay=delay_seconds)

async def process_llm(doc_key: str) -> None:
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
        pdf_url = f"https://archive.org/download/{ia_identifier}/document.pdf"

        async with httpx.AsyncClient() as client:
            resp = await client.get(pdf_url, follow_redirects=True, timeout=60.0)
            if resp.status_code != 200:
                msg = f"Could not fetch PDF from IA: {pdf_url}"
                raise RuntimeError(msg)
            pdf_bytes = resp.content

        # 3. Call Gemini
        analyzer = DecisionAnalyzer() # Picks up env vars
        result = await analyzer.analyze_decision(pdf_bytes)

        # 4. Save LLM output
        # To /tmp
        result_json = result.model_dump_json(indent=2)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp.write(result_json)
            tmp_path = Path(tmp.name)

        try:
            # Upload to IA
            if settings.IA_ACCESS_KEY:
                archive_service = InternetArchiveService()
            else:
                archive_service = LocalArchiveService(archive_root=Path("/tmp/archive"))

            await archive_service.upload_file(
                file_path=tmp_path,
                item_id=ia_identifier,
                metadata={"docKey": doc_key, "type": "llm_result"},
            )
        finally:
             if tmp_path.exists():
                os.unlink(tmp_path)

        # 5. Mark Done
        await doc_ref.update({
            "status": "llm_done",
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        logger.info("llm_complete", doc_key=doc_key)

    except Exception as e:
        logger.exception("llm_failed", doc_key=doc_key, error=str(e))

        # Schedule Retry (Cloud Tasks)
        # If this fails, we MUST raise to ensure Pub/Sub redelivery/NACK
        try:
            await schedule_retry(doc_key, data.get("attempts", {}).get("llm", 0) + 1)
        except Exception as retry_err:
             logger.exception("retry_schedule_failed_raising", doc_key=doc_key, error=str(retry_err))
             raise e # Raise original error to NACK

async def llm_worker(event: dict | Any, context: Any = None) -> None:
    """Pub/Sub trigger (or HTTP if called by Cloud Tasks).
    Analyzes PDF with Gemini and uploads result.

    Handles both:
    1. Pub/Sub Event (Background Function): event is dict with 'data'
    2. HTTP Request (Cloud Tasks): event is flask.Request object
    """
    doc_key = None

    # Check if event is likely a Flask Request object (has get_json)
    if hasattr(event, "get_json"):
        # HTTP Trigger
        try:
            request_json = event.get_json(silent=True)
            if request_json and "docKey" in request_json:
                doc_key = request_json["docKey"]
        except Exception as e:
            logger.exception("invalid_http_request", error=str(e))
            return
    elif isinstance(event, dict) and "data" in event:
        # Pub/Sub Trigger
        try:
            message_data = base64.b64decode(event["data"]).decode("utf-8")
            message = json.loads(message_data)
            doc_key = message.get("docKey")
        except Exception as e:
            logger.exception("invalid_pubsub_message", error=str(e))
            return
    else:
        logger.error("unknown_event_type", event_type=type(event).__name__)
        return

    if not doc_key:
        logger.error("missing_doc_key")
        return

    await process_llm(doc_key)
