"""Local embedding provider using sentence-transformers.

Runs entirely on CPU with no API calls, suitable for GitHub Actions
and local development. Default model: google/embeddinggemma-300m

The EmbeddingGemma-300M model features:
- 308M parameters, < 200MB RAM when quantized
- 100+ languages including PT-BR
- 768-dim output with MRL (truncatable to 256/128)
- 2048 token context window
- ~22ms inference on CPU

Usage:
    embedder = LocalEmbedder()
    vecs = embedder.embed(["Julgo procedente o pedido."], is_query=True)
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from functools import cached_property
from typing import TYPE_CHECKING

import numpy as np
import structlog


if TYPE_CHECKING:
    from pathlib import Path

    from sentence_transformers import SentenceTransformer


logger = structlog.get_logger()

# Primary model: EmbeddingGemma-300M (Google, Sept 2025)
# Instruction prefix for retrieval tasks (query side only)
EMBEDDING_GEMMA_MODEL = "google/embeddinggemma-300m"
EMBEDDING_GEMMA_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# Fallback: multilingual-e5-small (118M, instruction-tuned)
E5_SMALL_MODEL = "intfloat/multilingual-e5-small"
E5_SMALL_QUERY_PREFIX = "query: "
E5_SMALL_PASSAGE_PREFIX = "passage: "

# Default MRL truncation dimension for storage efficiency (from 768)
DEFAULT_DIMENSION = 256


class LocalEmbedder:
    """Local sentence-transformers embedder — no API, no cost.

    Wraps a ``sentence_transformers.SentenceTransformer`` model and exposes
    both sync and async interfaces. Async calls run the CPU-bound inference
    in a thread pool to avoid blocking the event loop.

    Args:
        model_name: HuggingFace model ID. Defaults to EmbeddingGemma-300M.
        cache_dir: Optional directory to cache downloaded model weights.
            Defaults to HuggingFace's default cache (~/.cache/huggingface).
        truncate_dim: If set, truncates embeddings to this dimension via MRL.
            EmbeddingGemma supports 128, 256, 768. Set to None to keep full dim.
        thread_workers: Number of threads for the executor pool. Default: 2.

    Example:
        embedder = LocalEmbedder()
        vecs = embedder.embed(["Julgo procedente."], is_query=True)
        # vecs.shape == (1, 256)

        # Async:
        vecs = await embedder.aembed(["texto"], is_query=False)
    """

    def __init__(
        self,
        model_name: str = EMBEDDING_GEMMA_MODEL,
        cache_dir: str | Path | None = None,
        truncate_dim: int | None = DEFAULT_DIMENSION,
        thread_workers: int = 2,
    ) -> None:
        """Initialize embedder with model and thread pool settings."""
        self.model_name = model_name
        self.cache_dir = str(cache_dir) if cache_dir else None
        self.truncate_dim = truncate_dim
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=thread_workers,
            thread_name_prefix="embedder",
        )
        logger.info(
            "local_embedder_init",
            model=model_name,
            truncate_dim=truncate_dim,
        )

    @cached_property
    def _model(self) -> SentenceTransformer:
        """Lazily load the SentenceTransformer model on first use."""
        try:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415
        except ImportError as exc:
            msg = (
                "sentence-transformers is required for LocalEmbedder. "
                "Install with: uv add sentence-transformers"
            )
            raise ImportError(msg) from exc

        logger.info("loading_local_model", model=self.model_name)
        model = SentenceTransformer(
            self.model_name,
            cache_folder=self.cache_dir,
            truncate_dim=self.truncate_dim,
            # trust_remote_code needed for some models (Jina, etc.)
            trust_remote_code=False,
        )
        logger.info(
            "local_model_loaded",
            model=self.model_name,
            embedding_dim=model.get_sentence_embedding_dimension(),
        )
        return model

    def _apply_prefix(self, texts: list[str], *, is_query: bool) -> list[str]:
        """Apply instruction prefix based on model and task type."""
        if self.model_name == EMBEDDING_GEMMA_MODEL:
            # EmbeddingGemma uses a query-side prefix only
            if is_query:
                return [EMBEDDING_GEMMA_QUERY_PREFIX + t for t in texts]
            return texts  # passage side: no prefix

        if self.model_name == E5_SMALL_MODEL:
            # E5 uses distinct prefixes for query and passage
            prefix = E5_SMALL_QUERY_PREFIX if is_query else E5_SMALL_PASSAGE_PREFIX
            return [prefix + t for t in texts]

        # Unknown model — no prefix
        return texts

    def embed(
        self,
        texts: list[str],
        *,
        is_query: bool = False,
        batch_size: int = 32,
        normalize: bool = True,
    ) -> np.ndarray:
        """Embed texts synchronously.

        Args:
            texts: List of strings to embed.
            is_query: True for query-side embeddings (adds instruction prefix).
                      False for document/passage embeddings (anchor set).
            batch_size: Internal batch size for the model.
            normalize: Whether to L2-normalize embeddings (recommended for
                       cosine similarity).

        Returns:
            NumPy array of shape (len(texts), embedding_dim).
        """
        encode_kwargs: dict = {
            "batch_size": batch_size,
            "normalize_embeddings": normalize,
            "show_progress_bar": False,
        }
        if self.model_name == EMBEDDING_GEMMA_MODEL:
            # Use the model's configured prompt names rather than a hardcoded string
            if is_query:
                encode_kwargs["prompt_name"] = "query"
            embeddings = self._model.encode(texts, **encode_kwargs)
        else:
            prefixed = self._apply_prefix(texts, is_query=is_query)
            embeddings = self._model.encode(prefixed, **encode_kwargs)
        return np.array(embeddings, dtype=np.float32)

    async def aembed(
        self,
        texts: list[str],
        *,
        is_query: bool = False,
        batch_size: int = 32,
        normalize: bool = True,
    ) -> np.ndarray:
        """Embed texts asynchronously (runs in thread pool).

        Same as ``embed()`` but async-safe. Uses a thread pool executor
        to avoid blocking the asyncio event loop during CPU-bound inference.

        Args:
            texts: List of strings to embed.
            is_query: True for query-side embeddings.
            batch_size: Internal batch size for the model.
            normalize: Whether to L2-normalize embeddings.

        Returns:
            NumPy array of shape (len(texts), embedding_dim).
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self.embed(
                texts, is_query=is_query, batch_size=batch_size, normalize=normalize
            ),
        )

    def embed_single(self, text: str, *, is_query: bool = False) -> np.ndarray:
        """Convenience wrapper for embedding a single text.

        Args:
            text: Single string to embed.
            is_query: True for query-side embedding.

        Returns:
            1-D NumPy array of shape (embedding_dim,).
        """
        return self.embed([text], is_query=is_query)[0]

    async def aembed_single(self, text: str, *, is_query: bool = False) -> np.ndarray:
        """Async version of ``embed_single``."""
        result = await self.aembed([text], is_query=is_query)
        return result[0]

    @property
    def embedding_dim(self) -> int:
        """Return the actual output embedding dimension."""
        if self.truncate_dim is not None:
            return self.truncate_dim
        return self._model.get_sentence_embedding_dimension()

    def __del__(self) -> None:
        """Cleanup thread pool on garbage collection."""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)
