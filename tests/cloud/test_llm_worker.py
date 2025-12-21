import json
import base64
import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, ANY
from causaganha.cloud.db import COLLECTION_NAME

# Import the module to test.
from causaganha.cloud.functions import llm

@pytest.fixture(autouse=True)
def mock_env_vars():
    """Sets environment variables for all tests in this module."""
    with patch("causaganha.config.settings.GCP_PROJECT", "test-project"), \
         patch("causaganha.config.settings.GCP_REGION", "us-central1"), \
         patch("causaganha.config.settings.TASKS_QUEUE", "test-queue"), \
         patch("causaganha.config.settings.FUNCTION_URL", "http://test-url"), \
         patch("causaganha.config.settings.IA_ACCESS_KEY", "fake-ia-key"), \
         patch.dict(os.environ, {"GOOGLE_API_KEY": "fake-key"}):
        yield

@pytest.fixture
def mock_firestore():
    with patch("causaganha.cloud.functions.llm.get_firestore_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client

@pytest.fixture
def mock_acquire_lock():
    with patch("causaganha.cloud.functions.llm.acquire_lock") as mock:
        mock.return_value = True
        yield mock

@pytest.fixture
def mock_httpx():
    with patch("causaganha.cloud.functions.llm.httpx.AsyncClient") as mock:
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = None

        # Default success response
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b"%PDF-1.4 fake pdf content"
        client.get.return_value = resp

        mock.return_value = client
        yield client

@pytest.fixture
def mock_analyzer():
    with patch("causaganha.cloud.functions.llm.DecisionAnalyzer") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance

        # Create a fake result
        result = MagicMock()
        result.model_dump_json.return_value = '{"winner": "Plaintiff"}'
        instance.analyze_decision.return_value = result

        yield instance

@pytest.fixture
def mock_archive_service():
    with patch("causaganha.cloud.functions.llm.InternetArchiveService") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value = instance
        yield instance

@pytest.fixture
def mock_tasks_client():
    with patch("causaganha.cloud.functions.llm.tasks_v2.CloudTasksClient") as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        yield instance

@pytest.mark.asyncio
async def test_llm_worker_success(
    mock_firestore,
    mock_acquire_lock,
    mock_httpx,
    mock_analyzer,
    mock_archive_service
):
    # Setup Firestore data
    doc_ref = MagicMock()
    mock_firestore.collection.return_value.document.return_value = doc_ref

    doc_snap = MagicMock()
    doc_snap.exists = True
    doc_snap.to_dict.return_value = {
        "ia_identifier": "test_ia_id",
        "status": "ingested"
    }
    doc_ref.get = AsyncMock(return_value=doc_snap)
    doc_ref.update = AsyncMock()

    # Create Pub/Sub event
    data = json.dumps({"docKey": "test_doc_key"})
    event = {"data": base64.b64encode(data.encode()).decode()}

    # Run
    await llm.llm_worker(event, {})

    # Verify
    mock_acquire_lock.assert_called_once()
    mock_firestore.collection.assert_called_with(COLLECTION_NAME)
    doc_ref.get.assert_called_once()

    # Verify PDF download
    mock_httpx.get.assert_called_with(
        "https://archive.org/download/test_ia_id/document.pdf",
        follow_redirects=True,
        timeout=60.0
    )

    # Verify Analysis
    mock_analyzer.analyze_decision.assert_called_with(b"%PDF-1.4 fake pdf content")

    # Verify Upload
    mock_archive_service.upload_file.assert_called_once()
    args, kwargs = mock_archive_service.upload_file.call_args
    assert kwargs["item_id"] == "test_ia_id"
    assert kwargs["metadata"]["type"] == "llm_result"

    # Verify DB Update
    doc_ref.update.assert_called_once()
    assert doc_ref.update.call_args[0][0]["status"] == "llm_done"

@pytest.mark.asyncio
async def test_llm_worker_http_trigger(
    mock_firestore,
    mock_acquire_lock,
    mock_httpx,
    mock_analyzer,
    mock_archive_service
):
    # Setup Firestore data
    doc_ref = MagicMock()
    mock_firestore.collection.return_value.document.return_value = doc_ref

    doc_snap = MagicMock()
    doc_snap.exists = True
    doc_snap.to_dict.return_value = {
        "ia_identifier": "test_ia_id",
        "status": "ingested"
    }
    doc_ref.get = AsyncMock(return_value=doc_snap)
    doc_ref.update = AsyncMock()

    # Create HTTP Request Mock
    mock_request = MagicMock()
    mock_request.get_json.return_value = {"docKey": "test_doc_key_http", "retry": True}
    # Mock hasattr to return True for get_json? No, MagicMock does that.

    # Run
    await llm.llm_worker(mock_request)

    # Verify
    doc_ref.update.assert_called_once()
    mock_httpx.get.assert_called()

@pytest.mark.asyncio
async def test_llm_worker_already_done(mock_firestore, mock_acquire_lock, mock_httpx):
    doc_ref = MagicMock()
    mock_firestore.collection.return_value.document.return_value = doc_ref

    doc_snap = MagicMock()
    doc_snap.exists = True
    doc_snap.to_dict.return_value = {
        "ia_identifier": "test_ia_id",
        "status": "llm_done" # Already done
    }
    doc_ref.get = AsyncMock(return_value=doc_snap)

    data = json.dumps({"docKey": "test_doc_key"})
    event = {"data": base64.b64encode(data.encode()).decode()}

    await llm.llm_worker(event, {})

    # Should exit early
    mock_httpx.get.assert_not_called()
    doc_ref.update.assert_not_called()

@pytest.mark.asyncio
async def test_llm_worker_retry_on_failure(
    mock_firestore,
    mock_acquire_lock,
    mock_httpx,
    mock_tasks_client
):
    doc_ref = MagicMock()
    mock_firestore.collection.return_value.document.return_value = doc_ref

    doc_snap = MagicMock()
    doc_snap.exists = True
    doc_snap.to_dict.return_value = {
        "ia_identifier": "test_ia_id",
        "status": "ingested",
        "attempts": {"llm": 0}
    }
    doc_ref.get = AsyncMock(return_value=doc_snap)

    # Simulate Download Error
    mock_httpx.get.side_effect = RuntimeError("IA Down")

    data = json.dumps({"docKey": "test_doc_key"})
    event = {"data": base64.b64encode(data.encode()).decode()}

    # Should NOT raise exception, but schedule retry
    await llm.llm_worker(event, {})

    # Verify Retry Scheduled
    mock_tasks_client.create_task.assert_called_once()
    call_args = mock_tasks_client.create_task.call_args[1]
    task_payload = json.loads(call_args["request"]["task"]["http_request"]["body"])
    assert task_payload["docKey"] == "test_doc_key"
    assert task_payload["retry"] is True
