"""Tests for embedding provider implementations."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from causaganha.v2.analysis.embedding_providers import (
    GoogleEmbeddingProvider,
    JinaEmbeddingProvider,
    create_embedding_provider,
)


class TestGoogleEmbeddingProvider:
    """Tests for Google embedding provider."""

    def test_initialization_with_api_key(self):
        """Test provider initialization with explicit API key."""
        provider = GoogleEmbeddingProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.dimension == 768
        assert provider.model == "text-embedding-004"

    def test_initialization_from_env(self, monkeypatch):
        """Test provider initialization from environment variable."""
        monkeypatch.setenv("GOOGLE_API_KEY", "env-key")
        provider = GoogleEmbeddingProvider()
        assert provider.api_key == "env-key"

    def test_initialization_without_api_key(self, monkeypatch):
        """Test provider initialization fails without API key."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        with pytest.raises(ValueError, match="Google API key must be provided"):
            GoogleEmbeddingProvider()

    def test_custom_dimension(self):
        """Test provider with custom dimension."""
        provider = GoogleEmbeddingProvider(api_key="test-key", dimension=512)
        assert provider.dimension == 512

    @pytest.mark.asyncio
    async def test_embed_text_success(self):
        """Test successful text embedding."""
        provider = GoogleEmbeddingProvider(api_key="test-key")

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "embedding": {"values": [0.1] * 768}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            embedding = await provider.embed_text("test text")
            assert len(embedding) == 768
            assert all(v == 0.1 for v in embedding)


class TestJinaEmbeddingProvider:
    """Tests for Jina AI embedding provider."""

    def test_initialization_with_api_key(self):
        """Test provider initialization with explicit API key."""
        provider = JinaEmbeddingProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.dimension == 1024
        assert provider.model == "jina-embeddings-v3"

    def test_initialization_from_env(self, monkeypatch):
        """Test provider initialization from environment variable."""
        monkeypatch.setenv("JINA_API_KEY", "env-key")
        provider = JinaEmbeddingProvider()
        assert provider.api_key == "env-key"

    def test_initialization_without_api_key(self, monkeypatch):
        """Test provider initialization fails without API key."""
        monkeypatch.delenv("JINA_API_KEY", raising=False)
        with pytest.raises(ValueError, match="Jina API key must be provided"):
            JinaEmbeddingProvider()

    def test_custom_dimension(self):
        """Test provider with custom dimension."""
        provider = JinaEmbeddingProvider(api_key="test-key", dimension=512)
        assert provider.dimension == 512

    def test_invalid_dimension(self):
        """Test provider rejects invalid dimensions."""
        with pytest.raises(ValueError, match="dimension must be between 256 and 1024"):
            JinaEmbeddingProvider(api_key="test-key", dimension=128)

    def test_task_mapping(self):
        """Test task type mapping."""
        provider = JinaEmbeddingProvider(api_key="test-key")
        assert provider.TASK_MAPPING["RETRIEVAL_QUERY"] == "retrieval.query"
        assert provider.TASK_MAPPING["RETRIEVAL_DOCUMENT"] == "retrieval.passage"

    @pytest.mark.asyncio
    async def test_embed_text_success(self):
        """Test successful text embedding."""
        provider = JinaEmbeddingProvider(api_key="test-key")

        # Mock the HTTP response (Jina uses OpenAI-compatible format)
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.2] * 1024}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            embedding = await provider.embed_text("test text")
            assert len(embedding) == 1024
            assert all(v == 0.2 for v in embedding)


class TestProviderFactory:
    """Tests for the embedding provider factory function."""

    def test_create_google_provider(self):
        """Test creating Google provider."""
        provider = create_embedding_provider("google", api_key="test-key")
        assert isinstance(provider, GoogleEmbeddingProvider)
        assert provider.api_key == "test-key"

    def test_create_jina_provider(self):
        """Test creating Jina provider."""
        provider = create_embedding_provider("jina", api_key="test-key")
        assert isinstance(provider, JinaEmbeddingProvider)
        assert provider.api_key == "test-key"

    def test_create_provider_case_insensitive(self):
        """Test provider name is case-insensitive."""
        provider1 = create_embedding_provider("GOOGLE", api_key="test-key")
        provider2 = create_embedding_provider("Google", api_key="test-key")
        assert isinstance(provider1, GoogleEmbeddingProvider)
        assert isinstance(provider2, GoogleEmbeddingProvider)

    def test_create_unsupported_provider(self):
        """Test error for unsupported provider."""
        with pytest.raises(ValueError, match="Unsupported embedding provider"):
            create_embedding_provider("openai", api_key="test-key")

    def test_create_provider_with_kwargs(self):
        """Test creating provider with additional kwargs."""
        provider = create_embedding_provider(
            "jina",
            api_key="test-key",
            dimension=768,
            model="jina-embeddings-v2",
        )
        assert provider.dimension == 768
        assert provider.model == "jina-embeddings-v2"
