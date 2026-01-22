import json
from datetime import date, timedelta
from typing import Any

import structlog
from google.cloud import pubsub_v1

from causaganha.infrastructure.cloud.db import (
    COLLECTION_NAME,
    DocState,
    compute_doc_key,
    get_firestore_client,
)
from causaganha.infrastructure.integrations.pje.client import PJeAPIClient


logger = structlog.get_logger()

from causaganha.config import settings


async def scheduler_tick(request: Any) -> str:
    """Cloud Scheduler trigger.
    Fetches new intimations and queues them for ingestion.
    """
    logger.info("scheduler_tick_start")

    db = get_firestore_client()
    publisher = pubsub_v1.PublisherClient()

    # Initialize PJe Client
    # Note: Using a dummy URL if not set, assuming client defaults are sane or overridden
    api_url = settings.PJE_API_URL
    client = PJeAPIClient(base_url=api_url)

    today = date.today()
    start_date = today - timedelta(days=settings.LOOKBACK_DAYS)

    # Example courts - could be env var
    courts = settings.COURTS

    processed_count = 0
    for court in courts:
        try:
            logger.info("fetching_court", court=court)
            intimations = await client.get_intimations_by_court(
                sigla_tribunal=court,
                data_inicio=start_date,
                data_fim=today,
            )

            for intimation in intimations:
                # 1. Normalize and compute docKey
                if not intimation.link:
                    continue

                doc_key = compute_doc_key(intimation.link)

                # 2. Upsert Firestore doc if new (Idempotency check)
                doc_ref = db.collection(COLLECTION_NAME).document(doc_key)
                doc = await doc_ref.get()

                doc_data = None
                if not doc.exists:
                    state = DocState(
                        docKey=doc_key,
                        status="new",
                        pdf_url=intimation.link,
                    )
                    await doc_ref.set(state.model_dump())
                    logger.info("created_new_doc", doc_key=doc_key)
                    doc_data = state.model_dump()
                else:
                    doc_data = doc.to_dict()

                # 3. Publish to topic_ingest
                status = doc_data.get("status")
                if status == "llm_done":
                    logger.debug("doc_done_skipping_publish", doc_key=doc_key)
                    continue

                message_json = json.dumps(
                    {
                        "docKey": doc_key,
                        "stage": "ingest",
                        "force": False,
                    },
                ).encode("utf-8")

                future = publisher.publish(settings.TOPIC_INGEST, message_json)
                future.result()  # Wait for publish
                processed_count += 1

        except Exception as e:
            logger.exception("scheduler_tick_failed", error=str(e))
            # continue

    logger.info("scheduler_tick_complete", processed=processed_count)
    return f"Processed {processed_count} items"
