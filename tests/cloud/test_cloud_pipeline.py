import json
import base64
import os
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from datetime import datetime

# Mocks for GCP services
@pytest.fixture
def mock_firestore():
    with patch("causaganha.cloud.db.firestore.AsyncClient") as mock:
        yield mock

@pytest.fixture
def mock_pubsub():
    with patch("google.cloud.pubsub_v1.PublisherClient") as mock:
        yield mock

@pytest.fixture
def mock_pubsub_ingest():
    with patch("google.cloud.pubsub_v1.PublisherClient") as mock:
        yield mock

@pytest.fixture
def mock_pje_client():
    with patch("causaganha.api.client.PJeAPIClient") as mock:
        yield mock

@pytest.fixture
def mock_doc_service():
    with patch("causaganha.services.document.DocumentService") as mock:
        yield mock

@pytest.fixture
def mock_ia_service():
    with patch("causaganha.services.archive.InternetArchiveService") as mock:
        yield mock

@pytest.mark.asyncio
async def test_scheduler_tick(mock_firestore, mock_pubsub, mock_pje_client):
    from causaganha.cloud.functions.scheduler import scheduler_tick

    # Setup PJe mock
    mock_client_instance = mock_pje_client.return_value
    # Make get_intimations_by_court awaitable
    mock_client_instance.get_intimations_by_court = AsyncMock(return_value=[
        MagicMock(link="http://example.com/doc.pdf")
    ])

    # Setup Firestore mock
    mock_db = mock_firestore.return_value
    mock_doc_ref = MagicMock()
    # Make set awaitable
    mock_doc_ref.set = AsyncMock()
    # Make get awaitable
    mock_doc_snapshot = MagicMock()
    mock_doc_snapshot.exists = False
    mock_doc_ref.get = AsyncMock(return_value=mock_doc_snapshot)

    mock_db.collection.return_value.document.return_value = mock_doc_ref

    # Setup PubSub mock
    mock_publisher = mock_pubsub.return_value
    mock_future = MagicMock()
    mock_publisher.publish.return_value = mock_future

    # Run
    result = await scheduler_tick(None)

    # Verify
    assert "Processed 1 items" in result
    mock_doc_ref.set.assert_called_once()
    mock_publisher.publish.assert_called_once()

    # Verify docKey generation
    args, _ = mock_doc_ref.set.call_args
    assert args[0]['pdf_url'] == "http://example.com/doc.pdf"
    assert args[0]['status'] == "new"

@pytest.mark.asyncio
async def test_ingest_worker(mock_firestore, mock_pubsub_ingest, mock_doc_service, mock_ia_service):
    from causaganha.cloud.functions.ingest import ingest_worker

    # Input event
    doc_key = "test_key"
    message = {"docKey": doc_key}
    event = {"data": base64.b64encode(json.dumps(message).encode()).decode()}

    # Setup Firestore
    mock_db = mock_firestore.return_value
    mock_transaction = MagicMock()
    mock_db.transaction.return_value = mock_transaction

    mock_doc_ref = MagicMock()
    mock_db.collection.return_value.document.return_value = mock_doc_ref

    # Transaction get (for lock)
    mock_snapshot = MagicMock()
    mock_snapshot.exists = True
    mock_snapshot.to_dict.return_value = {"lock_until": None}

    # Setup update to be awaitable
    mock_doc_ref.update = AsyncMock()
    # Setup get to be awaitable
    mock_doc_ref.get = AsyncMock(return_value=mock_snapshot)

    # Transactional get needs to work via the callback, which is hard to mock perfectly with the decorator.
    # So we mock `acquire_lock` directly.

    with patch("causaganha.cloud.functions.ingest.acquire_lock", new_callable=AsyncMock) as mock_lock, \
         patch.dict(os.environ, {"IA_ACCESS_KEY": "test"}) as mock_env:
        mock_lock.return_value = True

        # Setup DocService
        mock_doc_instance = mock_doc_service.return_value
        # Make download_pdf awaitable
        mock_doc_instance.download_pdf = AsyncMock(return_value=b"PDF_CONTENT")

        # Setup IA Service
        mock_ia_instance = mock_ia_service.return_value
        # Make upload_file awaitable
        mock_ia_instance.upload_file = AsyncMock(return_value="https://archive.org/details/test")

        # Setup doc data
        mock_snapshot.to_dict.return_value = {
            "pdf_url": "http://example.com/doc.pdf",
            "status": "new"
        }

        # Run
        await ingest_worker(event, None)

        # Verify
        mock_doc_instance.download_pdf.assert_called_with("http://example.com/doc.pdf")
        mock_ia_instance.upload_file.assert_called_once()
        mock_doc_ref.update.assert_called_with({
            "status": "pdf_uploaded",
            "ia_identifier": f"causaganha-{doc_key[:16]}",
            "updated_at": unittest.mock.ANY
        })
        mock_pubsub_ingest.return_value.publish.assert_called_once()

import unittest.mock
