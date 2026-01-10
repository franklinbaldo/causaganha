import base64
import json
from datetime import datetime
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from causaganha.domain.models import Intimation


# Mocks for GCP services
@pytest.fixture
def mock_firestore():
    # Patching firestore.AsyncClient inside causaganha.cloud.db
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
    with patch("causaganha.integrations.pje.client.PJeAPIClient") as mock:
        yield mock

@pytest.fixture
def mock_doc_service():
    # Patch where it is used: causaganha.cloud.functions.ingest
    with patch("causaganha.cloud.functions.ingest.DocumentService") as mock:
        yield mock

@pytest.fixture
def mock_ia_service():
    with patch("causaganha.cloud.functions.ingest.InternetArchiveService") as mock:
        yield mock

@pytest.mark.asyncio
async def test_scheduler_tick(mock_firestore, mock_pubsub, mock_pje_client) -> None:
    from causaganha.cloud.functions.scheduler import scheduler_tick

    # Setup PJe mock
    mock_client_instance = mock_pje_client.return_value
    # Make get_intimations_by_court awaitable
    mock_client_instance.get_intimations_by_court = AsyncMock(return_value=[
         Intimation(
                id=123,
                numero_processo="1234567-89.2024.8.22.0001",
                link="http://example.com/doc.pdf",
                data_disponibilizacao=datetime.now().date(),
                sigla_tribunal="TJRO",
                tipo_comunicacao="INTIMACAO",
                nome_orgao="Vara Civel",
                texto="Content",
                tipo_documento="DESPACHO",
                nome_classe="Procedimento Comum",
                hash="abc123hash",
            ),
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
    # Patching settings if needed, but defaults are fine for this test
    res = await scheduler_tick(None)

    # Verify
    assert "Processed 1 items" in res
    mock_doc_ref.set.assert_called_once()
    mock_publisher.publish.assert_called_once()

    # Verify docKey generation
    args, _ = mock_doc_ref.set.call_args
    assert args[0]["pdf_url"] == "http://example.com/doc.pdf"
    assert args[0]["status"] == "new"

@pytest.mark.asyncio
async def test_ingest_worker(mock_firestore, mock_pubsub_ingest, mock_doc_service, mock_ia_service) -> None:
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

    with patch("causaganha.cloud.functions.ingest.acquire_lock", new_callable=AsyncMock) as mock_lock, \
         patch("causaganha.config.settings.IA_ACCESS_KEY", "test"), \
         patch("causaganha.config.settings.TOPIC_LLM", "projects/test/topics/llm"):

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
            "status": "new",
        }

        # Run
        await ingest_worker(event, None)

        # Verify
        mock_doc_instance.download_pdf.assert_called_with("http://example.com/doc.pdf")
        mock_ia_instance.upload_file.assert_called_once()
        mock_doc_ref.update.assert_called_with({
            "status": "pdf_uploaded",
            "ia_identifier": f"causaganha-{doc_key[:16]}",
            "updated_at": ANY,
        })
        mock_pubsub_ingest.return_value.publish.assert_called_once()
