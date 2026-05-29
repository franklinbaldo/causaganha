from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from causaganha.analysis.api_embedder import ApiEmbedder


def mock_post_side_effect(url: str, **kwargs: Any) -> MagicMock:
    payload = kwargs.get("json", {})
    inputs = payload.get("input", [])
    resp = MagicMock()
    resp.json.return_value = {
        "data": [{"embedding": [0.1] * 1024} for _ in inputs],
        "usage": {"total_tokens": len(inputs) * 10},
    }
    resp.raise_for_status = MagicMock()
    return resp


async def mock_async_post_side_effect(url: str, **kwargs: Any) -> MagicMock:
    payload = kwargs.get("json", {})
    inputs = payload.get("input", [])
    resp = MagicMock()
    resp.json.return_value = {
        "data": [{"embedding": [0.2] * 1024} for _ in inputs],
        "usage": {"total_tokens": len(inputs) * 10},
    }
    resp.raise_for_status = MagicMock()
    return resp


def test_api_embedder_sync_jina() -> None:
    with patch("httpx.post", side_effect=mock_post_side_effect) as mock_post:
        embedder = ApiEmbedder(provider="jina", api_key="test_key")
        result = embedder.embed(["hello"], normalize=False)

        assert isinstance(result, np.ndarray)
        assert result.shape == (1, 1024)
        assert np.allclose(result, 0.1)

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer test_key"
        assert kwargs["json"]["model"] == "jina-embeddings-v3"
        assert kwargs["json"]["input"] == ["hello"]


@pytest.mark.asyncio
async def test_api_embedder_async_jina() -> None:
    mock_post = AsyncMock(side_effect=mock_async_post_side_effect)

    with patch("httpx.AsyncClient.post", mock_post):
        embedder = ApiEmbedder(provider="jina", api_key="test_key")
        result = await embedder.aembed(["hello_async"], normalize=False)

        assert isinstance(result, np.ndarray)
        assert result.shape == (1, 1024)
        assert np.allclose(result, 0.2)

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer test_key"
        assert kwargs["json"]["model"] == "jina-embeddings-v3"
        assert kwargs["json"]["input"] == ["hello_async"]


def test_api_embedder_sync_openrouter() -> None:
    with patch("httpx.post", side_effect=mock_post_side_effect) as mock_post:
        embedder = ApiEmbedder(provider="openrouter", api_key="test_key_or")
        result = embedder.embed(["hello_or"], normalize=False)

        assert isinstance(result, np.ndarray)
        assert result.shape == (1, 1024)
        assert np.allclose(result, 0.1)

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer test_key_or"
        assert kwargs["json"]["model"] == "perplexity/pplx-embed-v1-0.6b"
        assert kwargs["json"]["input"] == ["hello_or"]


@pytest.mark.asyncio
async def test_api_embedder_async_openrouter_concurrency() -> None:
    mock_post = AsyncMock(side_effect=mock_async_post_side_effect)

    with patch("httpx.AsyncClient.post", mock_post):
        embedder = ApiEmbedder(provider="openrouter", api_key="test_key_or")
        embedder._batch_size = 2
        texts = ["text1", "text2", "text3", "text4", "text5"]
        result = await embedder.aembed(texts, normalize=False, concurrency=2)

        assert isinstance(result, np.ndarray)
        assert result.shape == (5, 1024)
        assert np.allclose(result, 0.2)

        assert mock_post.call_count == 3
        _, first_kwargs = mock_post.call_args_list[0]
        assert first_kwargs["json"]["input"] == ["text1", "text2"]
        _, last_kwargs = mock_post.call_args_list[2]
        assert last_kwargs["json"]["input"] == ["text5"]


@pytest.mark.asyncio
async def test_api_embedder_async_smart_truncate() -> None:
    mock_post = AsyncMock(side_effect=mock_async_post_side_effect)

    with patch("httpx.AsyncClient.post", mock_post):
        embedder = ApiEmbedder(provider="openrouter", api_key="test_key_or")
        # Generate a text exceeding SMART_TRUNCATE_CHARS (100,000)
        long_text = "A" * 60_000 + "MIDDLE_MARKER" + "B" * 60_000
        await embedder.aembed([long_text], normalize=False)

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        sent_input = kwargs["json"]["input"][0]
        # Verify that smart_truncate was applied (input is truncated and has the join marker)
        assert "MIDDLE_MARKER" not in sent_input
        assert "[...]" in sent_input
        assert len(sent_input) == 100_000 + len("\n[...]\n")


@pytest.mark.asyncio
async def test_api_embedder_loop_affinity() -> None:
    embedder = ApiEmbedder(provider="jina", api_key="test_key")

    # Get loop in first run
    lock1 = embedder._async_rate_limit_lock
    budget_lock1 = embedder._async_budget_lock

    assert lock1 is not None
    assert budget_lock1 is not None

    # In same loop, it should return same lock
    assert embedder._async_rate_limit_lock is lock1
    assert embedder._async_budget_lock is budget_lock1

    # Mock a different event loop
    mock_loop = MagicMock()
    with patch("asyncio.get_running_loop", return_value=mock_loop):
        lock2 = embedder._async_rate_limit_lock
        budget_lock2 = embedder._async_budget_lock

        assert lock2 is not lock1
        assert budget_lock2 is not budget_lock1
