"""Local embedding provider using sentence-transformers.

Primary model: perplexity-ai/pplx-embed-v1-0.6b (MIT, open weights)

pplx-embed-v1-0.6b highlights:
- 0.6B params (Qwen3 backbone), 1024-dim output
- 32K token context window (handles complete judicial decisions without chunking)
- INT8 / binary quantization native — always compare via cosine, not dot product
- $0.004/1M tokens via API; run local for $0 cost (open weights, MIT license)
- For RAG use: pplx-embed-context-v1-0.6b ($0.008/1M) adds passage disambiguation

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

# ---------------------------------------------------------------------------
# Primary: Perplexity pplx-embed-v1 (MIT, Qwen3-based, 1024-dim, 32K context)
# ---------------------------------------------------------------------------
PPLX_EMBED_MODEL = "perplexity-ai/pplx-embed-v1-0.6b"
# RAG-optimized variant with passage disambiguation — same price tier difference
PPLX_EMBED_CONTEXT_MODEL = "perplexity-ai/pplx-embed-context-v1-0.6b"

# Models that use sentence-transformers prompt_name="query" on the query side
_PROMPT_NAME_MODELS = frozenset({PPLX_EMBED_MODEL, PPLX_EMBED_CONTEXT_MODEL})

# Models requiring trust_remote_code (Qwen3 custom code)
_TRUST_REMOTE_MODELS = frozenset({PPLX_EMBED_MODEL, PPLX_EMBED_CONTEXT_MODEL})

# ---------------------------------------------------------------------------
# Legacy / fallback models (kept for backward compat)
# ---------------------------------------------------------------------------
# EmbeddingGemma-300M (Google, 768-dim, 2048-token context)
EMBEDDING_GEMMA_MODEL = "google/embeddinggemma-300m"
EMBEDDING_GEMMA_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# multilingual-e5-small (118M, instruction-tuned)
E5_SMALL_MODEL = "intfloat/multilingual-e5-small"
E5_SMALL_QUERY_PREFIX = "query: "
E5_SMALL_PASSAGE_PREFIX = "passage: "

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
# pplx-embed-v1 outputs fixed 1024 dims (no MRL). Set None to keep full dims.
DEFAULT_DIMENSION: int | None = None

# Smart truncation guard. pplx-embed has 32K token context ≈ 100K chars of
# Portuguese legal text. Virtually no judicial intimação exceeds this.
_SMART_TRUNCATE_CHARS = 100_000


class LocalEmbedder:
    """Local sentence-transformers embedder — no API, no cost.

    Wraps a ``sentence_transformers.SentenceTransformer`` model and exposes
    both sync and async interfaces. Async calls run the CPU-bound inference
    in a thread pool to avoid blocking the event loop.

    Default model is ``pplx-embed-v1-0.6b`` (MIT, 1024-dim, 32K context).
    The 32K context window means full judicial decisions embed in a single
    pass — no chunking or mean-pooling required.

    Args:
        model_name: HuggingFace model ID.
        cache_dir: Optional directory to cache downloaded model weights.
        truncate_dim: If set, truncates embeddings via MRL. Only applicable
            to models that support MRL (e.g. EmbeddingGemma). Leave None
            for pplx-embed (fixed 1024-dim output).
        thread_workers: Number of threads for the executor pool.

    Example:
        embedder = LocalEmbedder()
        vecs = embedder.embed(["Julgo procedente."], is_query=True)
        # vecs.shape == (1, 1024)

        # RAG variant:
        embedder = LocalEmbedder(model_name=PPLX_EMBED_CONTEXT_MODEL)

        # Async:
        vecs = await embedder.aembed(["texto"], is_query=False)
    """

    def __init__(
        self,
        model_name: str = PPLX_EMBED_MODEL,
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
            trust_remote_code=self.model_name in _TRUST_REMOTE_MODELS,
        )
        logger.info(
            "local_model_loaded",
            model=self.model_name,
            embedding_dim=model.get_sentence_embedding_dimension(),
        )
        return model

    @staticmethod
    def _smart_truncate(text: str, max_chars: int = _SMART_TRUNCATE_CHARS) -> str:
        """Keep first half + last half of text when it exceeds max_chars.

        Safety net for extremely long texts. With pplx-embed's 32K context
        (~100K chars) this virtually never triggers for judicial documents.
        Preserves document head (parties, case number) and tail (dispositivo).
        """
        if len(text) <= max_chars:
            return text
        half = max_chars // 2
        return text[:half] + "\n[...]\n" + text[-half:]

    def _apply_prefix(self, texts: list[str], *, is_query: bool) -> list[str]:
        """Apply instruction prefix for models that don't use prompt_name."""
        if self.model_name == E5_SMALL_MODEL:
            prefix = E5_SMALL_QUERY_PREFIX if is_query else E5_SMALL_PASSAGE_PREFIX
            return [prefix + t for t in texts]
        if self.model_name == EMBEDDING_GEMMA_MODEL and is_query:
            return [EMBEDDING_GEMMA_QUERY_PREFIX + t for t in texts]
        return texts

    def embed(
        self,
        texts: list[str],
        *,
        is_query: bool = False,
        batch_size: int = 16,
        normalize: bool = True,
    ) -> np.ndarray:
        """Embed texts synchronously.

        Args:
            texts: List of strings to embed.
            is_query: True for query-side embeddings (adds instruction prefix).
                      False for document/passage embeddings (anchor set).
            batch_size: Internal batch size for the model. Default 16 is
                conservative for 32K-context models with long documents.
            normalize: L2-normalize embeddings. Required for correct cosine
                similarity with pplx-embed INT8 output.

        Returns:
            NumPy array of shape (len(texts), embedding_dim).
        """
        texts = [self._smart_truncate(t) for t in texts]
        encode_kwargs: dict = {
            "batch_size": batch_size,
            "normalize_embeddings": normalize,
            "show_progress_bar": False,
        }
        if self.model_name in _PROMPT_NAME_MODELS or self.model_name == EMBEDDING_GEMMA_MODEL:
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
        batch_size: int = 16,
        normalize: bool = True,
    ) -> np.ndarray:
        """Embed texts asynchronously (runs in thread pool).

        Same as ``embed()`` but async-safe. Uses a thread pool executor
        to avoid blocking the asyncio event loop during CPU-bound inference.

        Args:
            texts: List of strings to embed.
            is_query: True for query-side embeddings.
            batch_size: Internal batch size for the model.
            normalize: L2-normalize embeddings.

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
