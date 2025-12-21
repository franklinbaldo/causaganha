import hashlib
from datetime import UTC, datetime, timedelta
from typing import Literal

import structlog
from google.cloud import firestore
from pydantic import BaseModel, Field


logger = structlog.get_logger()

# Constants
COLLECTION_NAME = "docs"
LOCK_DURATION_SECONDS = 300  # 5 minutes


class DocState(BaseModel):
    """Firestore document state model."""

    docKey: str
    status: Literal["new", "pdf_uploaded", "llm_submitted", "llm_done", "error"]
    pdf_url: str
    ia_identifier: str | None = None
    pdf_filename: str = "document.pdf"
    llm_result_filename: str = "llm_result.json"
    upstream_etag: str | None = None
    pdf_sha256: str | None = None
    gemini_request_id: str | None = None
    attempts: dict[str, int] = Field(default_factory=dict)
    next_retry_at: datetime | None = None
    lock_until: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def get_firestore_client() -> firestore.AsyncClient:
    """Returns an async Firestore client."""
    return firestore.AsyncClient()


def compute_doc_key(url: str) -> str:
    """Computes a stable document key from the URL."""
    return hashlib.sha256(url.encode()).hexdigest()


async def acquire_lock(db: firestore.AsyncClient, doc_key: str, stage: str) -> bool:
    """Acquires a lock for the document for a specific stage."""
    doc_ref = db.collection(COLLECTION_NAME).document(doc_key)

    @firestore.async_transactional
    async def _update_in_transaction(transaction, ref):
        snapshot = await ref.get(transaction=transaction)
        if not snapshot.exists:
            return False

        data = snapshot.to_dict()
        lock_until = data.get("lock_until")

        # Check if locked
        if lock_until:
            # Convert to aware datetime if naive (Firestore sometimes returns naive UTC)
            if lock_until.tzinfo is None:
                lock_until = lock_until.replace(tzinfo=UTC)

            if lock_until > datetime.now(UTC):
                logger.warning("doc_locked", doc_key=doc_key, until=lock_until)
                return False

        # Lock it
        new_lock_until = datetime.now(UTC) + timedelta(seconds=LOCK_DURATION_SECONDS)
        transaction.update(
            ref, {"lock_until": new_lock_until, "updated_at": datetime.now(UTC)},
        )
        return True

    try:
        transaction = db.transaction()
        return await _update_in_transaction(transaction, doc_ref)
    except Exception as e:
        logger.exception("lock_acquisition_failed", doc_key=doc_key, error=str(e))
        return False
