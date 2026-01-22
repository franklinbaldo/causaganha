"""Tests for embedding provider implementations."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from causaganha.v2.analysis.embedding_models import (
    GOOGLE_GEMINI_768,
    JINA_V4_1024,
)
from causaganha.v2.analysis.providers import (
    GoogleProvider,
    JinaProvider,
    auto_select_provider,
    create_provider,
)


class TestGoogleEmbeddingProvider:
    """Test suite for Google embedding provider."""

    def setup_method(self):
        self.api_key = "test-key"
        with patch.dict("os.environ", {"GOOGLE_API_KEY": self.api_key}):
            self.provider = GoogleProvider()

    def test_initialization_with_api_key(self):
        """Test initialization with explicit API key."""
        provider = GoogleProvider(api_key="custom-key")
        assert provider.api_key == "custom-key"

    def test_initialization_with_env_var(self):
        """Test initialization using environment variable."""
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "env-key"}):
            provider = GoogleProvider()
            assert provider.api_key == "env-key"

    def test_initialization_failure(self):
        """Test initialization fails without API key."""
        with patch.dict("os.environ", clear=True):
            with pytest.raises(ValueError):
                GoogleProvider()

    @pytest.mark.asyncio
    async def test_embed_text_success(self):
        """Test successful embedding generation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "embedding": {"values": [0.1, 0.2, 0.3]},
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response,
            )

            embedding = await self.provider.embed_text(
                "test text",
                model=GOOGLE_GEMINI_768,
            )

            assert embedding == [0.1, 0.2, 0.3]

            # Verify request structure
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            _, kwargs = call_args
            assert "key" in kwargs["params"]
            assert "content" in kwargs["json"]
            assert kwargs["json"]["taskType"] == "RETRIEVAL_QUERY"

    @pytest.mark.asyncio
    async def test_embed_text_wrong_model(self):
        """Test error when using non-Google model."""
        with pytest.raises(ValueError):
            await self.provider.embed_text("test", model=JINA_V4_1024)


class TestJinaEmbeddingProvider:
    """Test suite for Jina embedding provider."""

    def setup_method(self):
        self.api_key = "test-key"
        with patch.dict("os.environ", {"JINA_API_KEY": self.api_key}):
            self.provider = JinaProvider()

    def test_initialization_with_api_key(self):
        """Test initialization with explicit API key."""
        provider = JinaProvider(api_key="custom-key")
        assert provider.api_key == "custom-key"

    @pytest.mark.asyncio
    async def test_embed_text_success(self):
        """Test successful embedding generation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * 1024}],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response,
            )

            embedding = await self.provider.embed_text(
                "test text",
                model=JINA_V4_1024,
            )

            assert len(embedding) == 1024
            assert embedding[0] == 0.1

            # Verify request
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            _, kwargs = call_args
            assert "Authorization" in kwargs["headers"]
            assert kwargs["json"]["model"] == "jina-embeddings-v4"


class TestProviderFactory:
    """Test suite for provider factory functions."""

    def test_create_provider_google(self):
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "key"}):
            provider = create_provider("google")
            assert isinstance(provider, GoogleProvider)

    def test_create_provider_jina(self):
        with patch.dict("os.environ", {"JINA_API_KEY": "key"}):
            provider = create_provider("jina")
            assert isinstance(provider, JinaProvider)

    def test_create_provider_invalid(self):
        with pytest.raises(ValueError):
            create_provider("invalid")

    @pytest.mark.asyncio
    async def test_auto_select_provider(self):
        """Test auto-selection logic."""
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "key"}):
            # Mock Google provider validation to succeed
            with patch(
                "causaganha.v2.analysis.providers.GoogleProvider.validate", new_callable=AsyncMock
            ) as mock_validate:
                mock_validate.return_value = True

                provider = await auto_select_provider(priority=["google"])
                assert isinstance(provider, GoogleProvider)

    @pytest.mark.asyncio
    async def test_auto_select_fallback(self):
        """Test fallback when first provider fails."""
        with patch.dict(
            "os.environ",
            {
                "GOOGLE_API_KEY": "key",
                "JINA_API_KEY": "key",
            },
        ):
            # Mock Jina (priority 1) to fail, Google (priority 2) to succeed
            with patch(
                "causaganha.v2.analysis.providers.JinaProvider.validate", new_callable=AsyncMock
            ) as mock_jina:
                mock_jina.return_value = False

                with patch(
                    "causaganha.v2.analysis.providers.GoogleProvider.validate",
                    new_callable=AsyncMock,
                ) as mock_google:
                    mock_google.return_value = True

                    provider = await auto_select_provider(priority=["jina", "google"])
                    assert isinstance(provider, GoogleProvider)
