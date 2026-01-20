"""Embedding service for generating text embeddings using multiple providers (Google, Jina AI, etc.)."""

import asyncio
import os
from typing import Literal

import structlog

from causaganha.v2.analysis.embedding_providers import (
    EmbeddingProvider,
    auto_select_provider,
    create_embedding_provider,
)

logger = structlog.get_logger()

# Embedding configuration defaults
EMBEDDING_MODEL = "text-embedding-004"  # Default Google model
EMBEDDING_DIMENSION = 768  # Default Google dimension
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
CONTEXTUAL_PREFIX = """Analise esta parte da decisão judicial para classificar o resultado (WIN/LOSS/PARTIAL/UNKNOWN).
Considere: vitória do autor, vitória do réu, parcial, ou resultado não claro."""


TaskType = Literal["RETRIEVAL_QUERY", "RETRIEVAL_DOCUMENT"]


class EmbeddingService:
    """Service for generating text embeddings with pluggable providers (Google, Jina AI, etc.)."""

    @classmethod
    async def create(
        cls,
        provider: str = "auto",
        priority: list[str] | None = None,
        api_key: str | None = None,
        model: str | None = None,
        dimension: int | None = None,
        max_retries: int = 3,
    ) -> "EmbeddingService":
        """Create an embedding service with automatic or manual provider selection.

        Args:
            provider: Embedding provider to use ('auto', 'google', or 'jina'). Default: 'auto'.
            priority: Priority order for auto-selection. Default: ["jina", "google"]
            api_key: API key for the provider (ignored for 'auto').
            model: Embedding model to use. If None, uses provider default.
            dimension: Embedding dimension. If None, uses provider default.
            max_retries: Maximum number of retry attempts.

        Returns:
            Initialized EmbeddingService instance.

        Raises:
            RuntimeError: If no valid provider can be found (when using 'auto').
        """
        provider = provider.lower()

        # Build provider kwargs
        provider_kwargs = {}
        if model:
            provider_kwargs["model"] = model
        if dimension:
            provider_kwargs["dimension"] = dimension

        if provider == "auto":
            # Auto-select provider based on priority
            selected_provider = await auto_select_provider(
                priority=priority,
                **provider_kwargs,
            )

            if selected_provider is None:
                raise RuntimeError(
                    "No valid embedding provider found. Please ensure at least one "
                    "provider API key is set (GOOGLE_API_KEY or JINA_API_KEY) and valid."
                )

            # Create instance with the selected provider
            instance = cls.__new__(cls)
            instance.provider = selected_provider
            instance.provider_name = (
                "google"
                if isinstance(selected_provider, type(create_embedding_provider("google", api_key="dummy")))
                else "jina"
            )
            instance.max_retries = max_retries

            # Determine provider name from class type
            provider_class_name = type(selected_provider).__name__
            if "Google" in provider_class_name:
                instance.provider_name = "google"
            elif "Jina" in provider_class_name:
                instance.provider_name = "jina"
            else:
                instance.provider_name = "unknown"

            logger.info(
                "embedding_service_created_auto",
                provider=instance.provider_name,
                dimension=instance.provider.dimension,
                max_retries=max_retries,
            )

            return instance
        else:
            # Create with specific provider (use regular __init__)
            return cls(
                provider=provider,
                api_key=api_key,
                model=model,
                dimension=dimension,
                max_retries=max_retries,
            )

    def __init__(
        self,
        provider: str = "google",
        api_key: str | None = None,
        model: str | None = None,
        dimension: int | None = None,
        max_retries: int = 3,
    ) -> None:
        """Initialize the embedding service with a specific provider.

        Note: For automatic provider selection, use EmbeddingService.create() instead.

        Args:
            provider: Embedding provider to use ('google' or 'jina'). Default: 'google'.
            api_key: API key for the provider. If None, reads from environment variable.
                     For Google: GOOGLE_API_KEY, For Jina: JINA_API_KEY
            model: Embedding model to use. If None, uses provider default.
                   Google default: text-embedding-004, Jina default: jina-embeddings-v3
            dimension: Embedding dimension. If None, uses provider default.
                      Google default: 768, Jina default: 1024
            max_retries: Maximum number of retry attempts (used by provider implementations).
        """
        self.provider_name = provider.lower()
        self.max_retries = max_retries

        # Build provider kwargs
        provider_kwargs = {}
        if model:
            provider_kwargs["model"] = model
        if dimension:
            provider_kwargs["dimension"] = dimension

        # Create the provider
        self.provider: EmbeddingProvider = create_embedding_provider(
            provider=self.provider_name,
            api_key=api_key,
            **provider_kwargs,
        )

        logger.info(
            "embedding_service_initialized",
            provider=self.provider_name,
            dimension=self.provider.dimension,
            max_retries=max_retries,
        )

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
        """Generate embedding for a single text using the configured provider.

        Args:
            text: Text to embed.
            task_type: Type of task (RETRIEVAL_QUERY or RETRIEVAL_DOCUMENT).
            add_prefix: Whether to add contextual prefix.

        Returns:
            Embedding vector (dimension depends on provider).

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        if add_prefix:
            text = self._add_contextual_prefix(text)

        # Delegate to the provider
        return await self.provider.embed_text(text, task_type=task_type)

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
            self.embed_text(text, task_type=task_type, add_prefix=add_prefix)
            for text in texts
        ]

        embeddings = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        successful = []
        failed = 0
        for emb in embeddings:
            if isinstance(emb, Exception):
                logger.error("embedding_failed_in_batch", error=str(emb))
                failed += 1
                # Zero vector fallback with provider's dimension
                successful.append([0.0] * self.provider.dimension)
            else:
                successful.append(emb)

        logger.info(
            "embedding_batch_complete",
            total=len(texts),
            successful=len(texts) - failed,
            failed=failed,
        )

        return successful

    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP,
    ) -> list[str]:
        """Split text into overlapping chunks.

        Args:
            text: Text to chunk.
            chunk_size: Size of each chunk in characters.
            overlap: Number of characters to overlap between chunks.

        Returns:
            List of text chunks.
        """
        if not text:
            return []

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Don't create tiny final chunks
            if end >= len(text):
                chunks.append(chunk)
                break

            chunks.append(chunk)
            start = end - overlap  # Step back by overlap amount

        logger.debug(
            "text_chunked",
            original_length=len(text),
            num_chunks=len(chunks),
            chunk_size=chunk_size,
            overlap=overlap,
        )

        return chunks

    async def embed_chunked_text(
        self,
        text: str,
        chunk_size: int = CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP,
        task_type: TaskType = "RETRIEVAL_QUERY",
    ) -> list[list[float]]:
        """Chunk text and generate embeddings for all chunks.

        Args:
            text: Text to process.
            chunk_size: Size of each chunk.
            overlap: Overlap between chunks.
            task_type: Task type for embeddings.

        Returns:
            List of embedding vectors for each chunk.
        """
        chunks = self.chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        return await self.embed_batch(chunks, task_type=task_type, add_prefix=True)
