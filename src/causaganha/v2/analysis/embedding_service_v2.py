"""Embedding service using the new Provider + Model architecture.

This is the new implementation that separates Provider (API service) from Model (configuration).
The old embedding_service.py is maintained for backward compatibility.
"""

import asyncio

import structlog

from causaganha.v2.analysis.embedding_models import (
    EmbeddingModel,
    get_default_model,
)
from causaganha.v2.analysis.providers import (
    EmbeddingProviderBase,
    TaskType,
    auto_select_provider,
    create_provider,
)
from causaganha.v2.analysis.text_chunker import TextChunker


logger = structlog.get_logger()

# Contextual prefix for legal document analysis
CONTEXTUAL_PREFIX = """Analise esta parte da decisão judicial para classificar o resultado (WIN/LOSS/PARTIAL/UNKNOWN).
Considere: vitória do autor, vitória do réu, parcial, ou resultado não claro."""


class EmbeddingService:
    """Service for generating text embeddings with separated Provider and Model architecture.

    This service uses:
    - Provider (EmbeddingProviderBase): API service (Jina AI, Google AI)
    - Model (EmbeddingModel): Configuration (model name, dimension, token limits)

    Example:
        # With auto-selection
        service = await EmbeddingService.create()

        # With specific provider and model
        from causaganha.v2.analysis.embedding_models import JINA_V4_1024
        service = await EmbeddingService.create(
            provider="jina",
            model=JINA_V4_1024
        )
    """

    def __init__(
        self,
        provider: EmbeddingProviderBase,
        model: EmbeddingModel,
    ) -> None:
        """Initialize the embedding service with a provider and model.

        Args:
            provider: Embedding provider (API service).
            model: Embedding model configuration.

        Raises:
            ValueError: If provider and model don't match.
        """
        # Validate that provider and model are compatible
        provider_type = provider.provider_name.lower()
        if model.provider != provider_type:
            msg = f"Provider type '{provider_type}' doesn't match model provider '{model.provider}'"
            raise ValueError(
                msg,
            )

        self.provider = provider
        self.model = model
        self.provider_name = provider.provider_name.lower()

        logger.info(
            "embedding_service_initialized",
            provider=self.provider_name,
            model=model.name,
            dimension=model.dimension,
            max_tokens=model.max_tokens,
        )

    @classmethod
    async def create(
        cls,
        provider: str | None = "auto",
        model: EmbeddingModel | None = None,
        priority: list[str] | None = None,
        api_key: str | None = None,
    ) -> "EmbeddingService":
        """Create an embedding service with automatic or manual provider selection.

        Args:
            provider: Provider name ('auto', 'jina', or 'google'). Default: 'auto'.
            model: EmbeddingModel to use. If None, uses provider's default model.
            priority: Priority order for auto-selection. Default: ["jina", "google"]
            api_key: API key for the provider (ignored for 'auto').

        Returns:
            Initialized EmbeddingService instance.

        Raises:
            RuntimeError: If no valid provider can be found (when using 'auto').

        Example:
            # Auto-select provider with default model
            service = await EmbeddingService.create()

            # Specific provider with custom model
            from causaganha.v2.analysis.embedding_models import JINA_V4_768
            service = await EmbeddingService.create(provider="jina", model=JINA_V4_768)
        """
        if provider == "auto":
            # Auto-select provider
            selected_provider = await auto_select_provider(priority=priority)

            if selected_provider is None:
                msg = (
                    "No valid embedding provider found. Please ensure at least one "
                    "provider API key is set (GOOGLE_API_KEY or JINA_API_KEY) and valid."
                )
                raise RuntimeError(
                    msg,
                )

            # Use provided model or default for selected provider
            if model is None:
                provider_type = selected_provider.provider_name.lower()
                model = get_default_model(provider_type)  # type: ignore

            return cls(provider=selected_provider, model=model)
        # Create specific provider
        selected_provider = create_provider(provider=provider, api_key=api_key)

        # Use provided model or default
        if model is None:
            model = get_default_model(provider)  # type: ignore

        return cls(provider=selected_provider, model=model)

    def _add_contextual_prefix(self, text: str) -> str:
        """Add contextual prefix to improve embedding quality.

        Args:
            text: Original text.

        Returns:
            Text with contextual prefix prepended.
        """
        return f"{CONTEXTUAL_PREFIX}\n\n{text}"

    async def embed_text(
        self,
        text: str,
        task_type: TaskType = "RETRIEVAL_QUERY",
        add_prefix: bool = True,
    ) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.
            task_type: Type of task (RETRIEVAL_QUERY or RETRIEVAL_DOCUMENT).
            add_prefix: Whether to add contextual prefix.

        Returns:
            Embedding vector (dimension from self.model).

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        if add_prefix:
            text = self._add_contextual_prefix(text)

        return await self.provider.embed_text(text, model=self.model, task_type=task_type)

    async def embed_batch(
        self,
        texts: list[str],
        task_type: TaskType = "RETRIEVAL_QUERY",
        add_prefix: bool = True,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts concurrently.

        Args:
            texts: List of texts to embed.
            task_type: Type of task for all texts.
            add_prefix: Whether to add contextual prefix to all texts.

        Returns:
            List of embedding vectors.
        """
        logger.info("embedding_batch_start", count=len(texts))

        tasks = [
            self.embed_text(text, task_type=task_type, add_prefix=add_prefix) for text in texts
        ]

        embeddings = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        successful = []
        failed = 0
        for emb in embeddings:
            if isinstance(emb, Exception):
                logger.error("embedding_failed_in_batch", error=str(emb))
                failed += 1
                # Zero vector fallback with model's dimension
                successful.append([0.0] * self.model.dimension)
            else:
                successful.append(emb)

        logger.info(
            "embedding_batch_complete",
            total=len(texts),
            successful=len(texts) - failed,
            failed=failed,
        )

        return successful

    def chunk_text(
        self,
        text: str,
        strategy: str = "auto",
        overlap_tokens: int = 128,
    ) -> list[str]:
        """Split text into chunks suitable for embedding.

        Uses the model's max_tokens to determine chunk size.

        Args:
            text: Text to chunk.
            strategy: Chunking strategy ('auto', 'sections', or 'sliding_window').
            overlap_tokens: Number of tokens to overlap between chunks.

        Returns:
            List of text chunks.
        """
        if not text or not text.strip():
            return []

        chunker = TextChunker(
            max_tokens=self.model.max_tokens,
            overlap_tokens=overlap_tokens,
        )

        return chunker.chunk_text(text, strategy=strategy)

    async def embed_chunked_text(
        self,
        text: str,
        task_type: TaskType = "RETRIEVAL_QUERY",
        strategy: str = "auto",
    ) -> list[list[float]]:
        """Chunk text dynamically and generate embeddings for all chunks.

        Uses dynamic chunking based on the model's token limit. For Jina v4,
        this allows up to 32K tokens per chunk. For Google Gemini, this limits
        chunks to 2K tokens.

        Args:
            text: Text to process.
            task_type: Task type for embeddings.
            strategy: Chunking strategy ('auto', 'sections', or 'sliding_window').
                     'auto' uses semantic sections for legal docs, sliding window otherwise.

        Returns:
            List of embedding vectors for each chunk.
        """
        # Create chunker from model's token limit
        chunker = TextChunker(
            max_tokens=self.model.max_tokens,
            overlap_tokens=128,
        )

        chunks = chunker.chunk_text(text, strategy=strategy)

        logger.info(
            "dynamic_chunking_complete",
            provider=self.provider_name,
            model=self.model.name,
            max_tokens=self.model.max_tokens,
            num_chunks=len(chunks),
            strategy=strategy,
        )

        return await self.embed_batch(chunks, task_type=task_type, add_prefix=True)
