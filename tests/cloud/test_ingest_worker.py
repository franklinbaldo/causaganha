import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import module under test
from causaganha.cloud.functions import ingest


@pytest.fixture(autouse=True)
def mock_env_vars():
    """Sets environment variables for all tests in this module."""
    with patch("causaganha.config.settings.GCP_PROJECT", "test-project"), \
         patch("causaganha.config.settings.TOPIC_LLM", "projects/test-project/topics/llm"), \
         patch("causaganha.config.settings.IA_ACCESS_KEY", "fake-ia-key"):
        yield

@pytest.fixture
def mock_firestore():
    with patch("causaganha.cloud.functions.ingest.get_firestore_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client

@pytest.fixture
def mock_publisher():
    with patch("causaganha.cloud.functions.ingest.pubsub_v1.PublisherClient") as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        yield instance

@pytest.fixture
def mock_acquire_lock():
    with patch("causaganha.cloud.functions.ingest.acquire_lock") as mock:
        mock.return_value = True
        yield mock

@pytest.fixture
def mock_doc_service():
    with patch("causaganha.cloud.functions.ingest.DocumentService") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.download_pdf.return_value = b"%PDF-1.4 fake content"
        yield instance

@pytest.fixture
def mock_archive_service():
    with patch("causaganha.cloud.functions.ingest.InternetArchiveService") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        instance.upload_file.return_value = "https://archive.org/details/test_id"
        yield instance

@pytest.mark.asyncio
async def test_ingest_worker_success(
    mock_firestore,
    mock_publisher,
    mock_acquire_lock,
    mock_doc_service,
    mock_archive_service,
) -> None:
    # Setup Firestore
    doc_ref = MagicMock()
    mock_firestore.collection.return_value.document.return_value = doc_ref

    doc_snap = MagicMock()
    doc_snap.exists = True
    doc_snap.to_dict.return_value = {
        "pdf_url": "http://court.gov.br/doc.pdf",
        "status": "new",
    }
    doc_ref.get = AsyncMock(return_value=doc_snap)
    doc_ref.update = AsyncMock()

    # Create Event
    data = json.dumps({"docKey": "test_doc_key"})
    event = {"data": base64.b64encode(data.encode()).decode()}

    # Run
    await ingest.ingest_worker(event, {})

    # Verify
    mock_acquire_lock.assert_called_once()

    # Verify Download
    mock_doc_service.download_pdf.assert_called_with("http://court.gov.br/doc.pdf")

    # Verify Upload
    mock_archive_service.upload_file.assert_called_once()
    args, _kwargs = mock_archive_service.upload_file.call_args
    # signature: upload_file(file_path, item_id, metadata)
    assert args[1] == "causaganha-test_doc_key" # item_id is 2nd arg
    assert args[2]["url"] == "http://court.gov.br/doc.pdf"

    # Verify Filename Contract (Must be document.pdf)
    file_path = args[0]
    assert str(file_path).endswith("document.pdf")

    # Verify Status Update
    doc_ref.update.assert_called_once()
    assert doc_ref.update.call_args[0][0]["status"] == "pdf_uploaded"
    assert doc_ref.update.call_args[0][0]["ia_identifier"] == "causaganha-test_doc_key"

    # Verify Pub/Sub Next Stage
    mock_publisher.publish.assert_called_once()
    call_args = mock_publisher.publish.call_args
    assert call_args[0][0] == "projects/test-project/topics/llm"
    msg_data = json.loads(call_args[0][1])
    assert msg_data["docKey"] == "test_doc_key"
    assert msg_data["stage"] == "llm"

@pytest.mark.asyncio
async def test_ingest_worker_already_done(
    mock_firestore,
    mock_publisher,
    mock_acquire_lock,
    mock_doc_service,
) -> None:
    doc_ref = MagicMock()
    mock_firestore.collection.return_value.document.return_value = doc_ref

    doc_snap = MagicMock()
    doc_snap.exists = True
    doc_snap.to_dict.return_value = {
        "pdf_url": "http://court.gov.br/doc.pdf",
        "status": "pdf_uploaded", # Already done
    }
    doc_ref.get = AsyncMock(return_value=doc_snap)

    data = json.dumps({"docKey": "test_doc_key"})
    event = {"data": base64.b64encode(data.encode()).decode()}

    # Run
    await ingest.ingest_worker(event, {})

    # Should skip download/upload but publish next stage
    mock_doc_service.download_pdf.assert_not_called()
    mock_publisher.publish.assert_called_once()

@pytest.mark.asyncio
async def test_ingest_worker_failure(
    mock_firestore,
    mock_publisher,
    mock_acquire_lock,
    mock_doc_service,
) -> None:
    doc_ref = MagicMock()
    mock_firestore.collection.return_value.document.return_value = doc_ref

    doc_snap = MagicMock()
    doc_snap.exists = True
    doc_snap.to_dict.return_value = {
        "pdf_url": "http://court.gov.br/doc.pdf",
        "status": "new",
    }
    doc_ref.get = AsyncMock(return_value=doc_snap)

    # Simulate Download Fail
    mock_doc_service.download_pdf.side_effect = Exception("Download Fail")

    data = json.dumps({"docKey": "test_doc_key"})
    event = {"data": base64.b64encode(data.encode()).decode()}

    # Should raise exception
    with pytest.raises(Exception, match="Download Fail"):
        await ingest.ingest_worker(event, {})
