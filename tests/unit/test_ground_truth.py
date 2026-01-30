from unittest.mock import AsyncMock, MagicMock

import pytest

lancedb = pytest.importorskip("lancedb", reason="lancedb is an optional dependency (extras: embeddings)")

from causaganha.analysis.ground_truth import GroundTruthManager  # noqa: E402


@pytest.fixture
def mock_vector_store():
    return MagicMock()


@pytest.fixture
def mock_embedding_service():
    service = MagicMock()
    service.embed_batch = AsyncMock()
    service.embed_text = AsyncMock()
    return service


@pytest.fixture
def manager(mock_vector_store, mock_embedding_service):
    return GroundTruthManager(
        vector_store=mock_vector_store,
        embedding_service=mock_embedding_service,
    )


def test_init_store_creates_table(manager, mock_vector_store):
    mock_vector_store.table_exists.return_value = False

    manager.init_store()

    mock_vector_store.create_table.assert_called_once()
    args, _ = mock_vector_store.create_table.call_args
    assert args[0] == "ground_truth"
    assert len(args[1]) == 1
    assert args[1][0]["intimation_id"] == 0


def test_init_store_skips_if_exists(manager, mock_vector_store):
    mock_vector_store.table_exists.return_value = True

    manager.init_store()

    mock_vector_store.create_table.assert_not_called()


def test_init_store_overwrites(manager, mock_vector_store):
    mock_vector_store.table_exists.return_value = False

    manager.init_store(overwrite=True)

    mock_vector_store.delete_table.assert_called_once_with("ground_truth")
    mock_vector_store.create_table.assert_called_once()


@pytest.mark.asyncio
async def test_search_calls_vector_store(manager, mock_vector_store, mock_embedding_service):
    mock_embedding_service.embed_text.return_value = [0.1] * 1024
    mock_vector_store.search.return_value = [{"text": "result", "score": 0.9}]

    results = await manager.search("query text", k=3)

    assert len(results) == 1
    assert results[0]["text"] == "result"
    mock_embedding_service.embed_text.assert_called_once_with(
        "query text",
        task_type="RETRIEVAL_QUERY",
        add_prefix=True,
    )
    mock_vector_store.search.assert_called_once_with("ground_truth", [0.1] * 1024, k=3)


@pytest.mark.asyncio
async def test_sync_from_db_no_records(manager):
    con = MagicMock()
    con.con.execute.return_value.fetchall.return_value = []

    result = await manager.sync_from_db(con)

    assert result["synced"] == 0
    assert result["status"] == "no_data"


@pytest.mark.asyncio
async def test_sync_from_db_successful_sync(manager, mock_vector_store, mock_embedding_service):
    con = MagicMock()
    # Mock DuckDB records: (id, text, outcome)
    con.con.execute.return_value.fetchall.return_value = [
        (1, "Text 1", "WIN"),
        (2, "Text 2", "LOSS"),
    ]

    # Mock existing IDs in vector store
    mock_vector_store.table_exists.return_value = True
    mock_table = MagicMock()
    mock_df = MagicMock()
    mock_df.empty = False
    mock_df.__contains__.return_value = True  # for "intimation_id" in df.columns
    mock_df.columns = ["intimation_id"]
    mock_df["intimation_id"].tolist.return_value = [1]  # ID 1 already exists
    mock_table.to_pandas.return_value = mock_df
    mock_vector_store.get_table.return_value = mock_table

    mock_embedding_service.embed_batch.return_value = [[0.2] * 1024]

    result = await manager.sync_from_db(con)

    assert result["synced"] == 1
    assert result["status"] == "success"

    # Verify only record 2 was synced
    mock_embedding_service.embed_batch.assert_called_once_with(
        ["Text 2"],
        task_type="RETRIEVAL_DOCUMENT",
        add_prefix=True,
    )
    mock_vector_store.add_documents.assert_called_once()
    args, _ = mock_vector_store.add_documents.call_args
    assert args[0] == "ground_truth"
    assert args[1][0]["intimation_id"] == 2
