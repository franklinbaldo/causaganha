"""API-based embedding provider: Jina AI or OpenRouter.

Drops in as a replacement for LocalEmbedder — same interface, no GPU required.

Provider strategy
-----------------
1. **Jina AI** (default) — ``jina-embeddings-v3``, 10 M free tokens/month.
   Set ``JINA_API_KEY``. Hard stops at budget to avoid surprise charges.
2. **OpenRouter** — ``perplexity/pplx-embed-v1-0.6b`` (default), MIT, 32K context.
   Set ``OPENROUTER_API_KEY``. Good for large corpora without a token budget.

Usage
-----
    # Jina (default)
    embedder = ApiEmbedder()                          # reads JINA_API_KEY
    vecs = embedder.embed(["Julgo procedente."], is_query=True)
    print(embedder.token_budget_remaining)            # tokens left this month

    # Async (concurrent batching client-side)
    import asyncio
    embedder = ApiEmbedder(provider="openrouter")
    async def main():
        vecs = await embedder.aembed(texts)
    asyncio.run(main())
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import TYPE_CHECKING, Literal

import numpy as np
import structlog

from .text_truncate import smart_truncate


if TYPE_CHECKING:
    import httpx


logger = structlog.get_logger()

Provider = Literal["jina", "openrouter"]

# ---------------------------------------------------------------------------
# Provider constants
# ---------------------------------------------------------------------------

# Jina jina-embeddings-v3 (multilingual, PT-BR native)
JINA_MODEL = "jina-embeddings-v3"
JINA_EMBED_DIM = 1024
JINA_BATCH_SIZE = 128
JINA_ENDPOINT = "https://api.jina.ai/v1/embeddings"
JINA_RPM_LIMIT = 500  # free-tier RPM
JINA_FREE_TOKEN_BUDGET = 10_000_000  # 10M tokens/month free tier
JINA_TOKEN_WARN_THRESHOLD = 0.90  # warn at 90% consumed

# OpenRouter embedding models (supports perplexity and llama-nemotron)
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/embeddings"
OPENROUTER_DEFAULT_MODEL = "perplexity/pplx-embed-v1-0.6b"
OPENROUTER_BATCH_SIZE = 128
OPENROUTER_RPM_LIMIT = 1000

_RATE_LIMIT_WINDOW = 60.0  # sliding window in seconds for RPM enforcement


class ApiEmbedder:
    """API-backed embedder — no GPU, no local model download.

    Args:
        provider: ``"jina"`` or ``"openrouter"``.
        api_key: API key. Falls back to ``JINA_API_KEY`` / ``OPENROUTER_API_KEY``
            environment variables.
        truncate_dim: Optional MRL truncation.
            ``None`` keeps the full dimension.
        rpm_limit: Requests-per-minute cap. Defaults to the provider free tier.
    """

    def __init__(
        self,
        provider: Provider = "jina",  # Jina first: 10M free tokens/month
        api_key: str | None = None,
        truncate_dim: int | None = None,
        rpm_limit: int | None = None,
        token_budget: int = JINA_FREE_TOKEN_BUDGET,
        model: str | None = None,
    ) -> None:
        """Initialise the API embedder for the specified provider."""
        self.provider = provider
        self.truncate_dim = truncate_dim

        if provider == "jina":
            self._api_key = api_key or os.environ.get("JINA_API_KEY", "")
            if not self._api_key:
                msg = "JINA_API_KEY not set. Get one at https://jina.ai/?sui=apikey"
                raise ValueError(msg)
            self._batch_size = JINA_BATCH_SIZE
            self._rpm_limit = rpm_limit or JINA_RPM_LIMIT
            self._embed_dim = truncate_dim or JINA_EMBED_DIM
            self._token_budget = token_budget
            self._tokens_used = 0

        elif provider == "openrouter":
            self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
            if not self._api_key:
                msg = "OPENROUTER_API_KEY not set. Get one at https://openrouter.ai/"
                raise ValueError(msg)
            self._model = model or OPENROUTER_DEFAULT_MODEL
            self._batch_size = OPENROUTER_BATCH_SIZE
            self._rpm_limit = rpm_limit or OPENROUTER_RPM_LIMIT

            # Select dimensions based on model choice
            default_dim = 2048 if "nemotron" in self._model else 1024
            self._embed_dim = truncate_dim or default_dim
            self._token_budget = None
            self._tokens_used = 0

        else:
            msg = f"Unknown provider: {provider!r}. Choose 'jina' or 'openrouter'."
            raise ValueError(msg)

        self._request_times: list[float] = []
        logger.info(
            "api_embedder_init",
            provider=provider,
            embed_dim=self._embed_dim,
            rpm_limit=self._rpm_limit,
            token_budget=self._token_budget,
        )

    @property
    def _async_rate_limit_lock(self) -> asyncio.Lock:
        """Lazily initialize the asyncio Lock to avoid event loop attachment issues."""
        if not hasattr(self, "_rate_limit_lock_obj"):
            self._rate_limit_lock_obj = asyncio.Lock()
        return self._rate_limit_lock_obj

    def _rate_limit(self) -> None:
        """Block until we are within the RPM limit (sliding 60-second window)."""
        now = time.monotonic()
        self._request_times = [t for t in self._request_times if now - t < _RATE_LIMIT_WINDOW]
        if len(self._request_times) >= self._rpm_limit:
            sleep_for = _RATE_LIMIT_WINDOW - (now - self._request_times[0]) + 0.1
            if sleep_for > 0:
                logger.debug("api_rate_limit_sleep", seconds=round(sleep_for, 2))
                time.sleep(sleep_for)
        self._request_times.append(time.monotonic())

    async def _arate_limit(self) -> None:
        """Block asynchronously until we are within the RPM limit (sliding 60-second window)."""
        async with self._async_rate_limit_lock:
            now = time.monotonic()
            self._request_times = [t for t in self._request_times if now - t < _RATE_LIMIT_WINDOW]
            if len(self._request_times) >= self._rpm_limit:
                sleep_for = _RATE_LIMIT_WINDOW - (now - self._request_times[0]) + 0.1
                if sleep_for > 0:
                    logger.debug("api_rate_limit_sleep", seconds=round(sleep_for, 2))
                    await asyncio.sleep(sleep_for)
            self._request_times.append(time.monotonic())

    # ------------------------------------------------------------------
    # Provider-specific batch embed
    # ------------------------------------------------------------------

    def _embed_batch_jina(self, texts: list[str], *, is_query: bool) -> np.ndarray:
        import httpx  # noqa: PLC0415

        # Estimate token usage (Jina counts ~1 token ≈ 4 chars on average)
        estimated_tokens = sum(max(1, len(t) // 4) for t in texts)
        if self._token_budget is not None:
            remaining = self._token_budget - self._tokens_used
            if estimated_tokens > remaining:
                msg = (
                    f"Jina token budget exhausted: "
                    f"{self._tokens_used:,}/{self._token_budget:,} used. "
                    "Switch to provider='openrouter' or get a new Jina API key."
                )
                raise RuntimeError(msg)
            usage_pct = (self._tokens_used + estimated_tokens) / self._token_budget
            if usage_pct >= JINA_TOKEN_WARN_THRESHOLD:
                logger.warning(
                    "jina_token_budget_nearly_exhausted",
                    tokens_used=self._tokens_used,
                    budget=self._token_budget,
                    pct=round(usage_pct * 100, 1),
                )

        task = "retrieval.query" if is_query else "retrieval.passage"
        payload: dict = {
            "model": JINA_MODEL,
            "input": texts,
            "task": task,
            "late_chunking": False,
        }
        if self.truncate_dim:
            payload["dimensions"] = self.truncate_dim

        self._rate_limit()
        resp = httpx.post(
            JINA_ENDPOINT,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        # Track actual tokens reported by the API
        actual_tokens = data.get("usage", {}).get("total_tokens", estimated_tokens)
        self._tokens_used += actual_tokens
        logger.debug(
            "jina_tokens_used",
            batch_tokens=actual_tokens,
            total_tokens_used=self._tokens_used,
            budget=self._token_budget,
        )

        return np.array([d["embedding"] for d in data["data"]], dtype=np.float32)

    def _embed_batch_openrouter(self, texts: list[str]) -> np.ndarray:
        import httpx  # noqa: PLC0415

        payload: dict = {
            "model": self._model,
            "input": texts,
        }
        # No MRL `dimensions` param — pplx-embed doesn't support it;
        # client-side truncation below handles truncate_dim instead.

        self._rate_limit()
        resp = httpx.post(
            OPENROUTER_ENDPOINT,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/franklinbaldo/causaganha",
            },
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        actual_tokens = data.get("usage", {}).get("total_tokens", 0)
        self._tokens_used += actual_tokens
        logger.debug(
            "openrouter_tokens_used",
            batch_tokens=actual_tokens,
            total_tokens_used=self._tokens_used,
        )

        embeddings = np.array([d["embedding"] for d in data["data"]], dtype=np.float32)
        if self.truncate_dim and embeddings.shape[1] > self.truncate_dim:
            embeddings = embeddings[:, : self.truncate_dim]
        return embeddings

    async def _aembed_batch_jina(
        self, client: httpx.AsyncClient, texts: list[str], *, is_query: bool
    ) -> np.ndarray:
        # Estimate token usage (Jina counts ~1 token ≈ 4 chars on average)
        estimated_tokens = sum(max(1, len(t) // 4) for t in texts)
        if self._token_budget is not None:
            remaining = self._token_budget - self._tokens_used
            if estimated_tokens > remaining:
                msg = (
                    f"Jina token budget exhausted: "
                    f"{self._tokens_used:,}/{self._token_budget:,} used. "
                    "Switch to provider='openrouter' or get a new Jina API key."
                )
                raise RuntimeError(msg)
            usage_pct = (self._tokens_used + estimated_tokens) / self._token_budget
            if usage_pct >= JINA_TOKEN_WARN_THRESHOLD:
                logger.warning(
                    "jina_token_budget_nearly_exhausted",
                    tokens_used=self._tokens_used,
                    budget=self._token_budget,
                    pct=round(usage_pct * 100, 1),
                )

        task = "retrieval.query" if is_query else "retrieval.passage"
        payload: dict = {
            "model": JINA_MODEL,
            "input": texts,
            "task": task,
            "late_chunking": False,
        }
        if self.truncate_dim:
            payload["dimensions"] = self.truncate_dim

        await self._arate_limit()
        resp = await client.post(
            JINA_ENDPOINT,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        # Track actual tokens reported by the API
        actual_tokens = data.get("usage", {}).get("total_tokens", estimated_tokens)
        self._tokens_used += actual_tokens
        logger.debug(
            "jina_tokens_used",
            batch_tokens=actual_tokens,
            total_tokens_used=self._tokens_used,
            budget=self._token_budget,
        )

        return np.array([d["embedding"] for d in data["data"]], dtype=np.float32)

    async def _aembed_batch_openrouter(
        self, client: httpx.AsyncClient, texts: list[str]
    ) -> np.ndarray:
        payload: dict = {
            "model": self._model,
            "input": texts,
        }

        await self._arate_limit()
        resp = await client.post(
            OPENROUTER_ENDPOINT,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/franklinbaldo/causaganha",
            },
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        actual_tokens = data.get("usage", {}).get("total_tokens", 0)
        self._tokens_used += actual_tokens
        logger.debug(
            "openrouter_tokens_used",
            batch_tokens=actual_tokens,
            total_tokens_used=self._tokens_used,
        )

        embeddings = np.array([d["embedding"] for d in data["data"]], dtype=np.float32)
        if self.truncate_dim and embeddings.shape[1] > self.truncate_dim:
            embeddings = embeddings[:, : self.truncate_dim]
        return embeddings

    # ------------------------------------------------------------------
    # Public interface (matches LocalEmbedder)
    # ------------------------------------------------------------------

    def embed(
        self,
        texts: list[str],
        *,
        is_query: bool = False,
        batch_size: int | None = None,
        normalize: bool = True,
    ) -> np.ndarray:
        """Embed texts via API, batching automatically.

        Args:
            texts: List of strings to embed.
            is_query: True for query-side task type.
            batch_size: Override default provider batch size.
            normalize: L2-normalize embeddings (recommended for cosine similarity).

        Returns:
            NumPy array of shape ``(len(texts), embed_dim)``.
        """
        # Guard against documents exceeding the model context: keep head+tail,
        # drop the middle (preserves parties/case number + dispositivo).
        texts = [smart_truncate(t) for t in texts]
        bs = batch_size or self._batch_size
        chunks = [texts[i : i + bs] for i in range(0, len(texts), bs)]
        parts: list[np.ndarray] = []

        for chunk in chunks:
            if self.provider == "openrouter":
                emb = self._embed_batch_openrouter(chunk)
            else:
                emb = self._embed_batch_jina(chunk, is_query=is_query)
            parts.append(emb)

        result = np.vstack(parts)
        if normalize:
            norms = np.linalg.norm(result, axis=1, keepdims=True)
            result = result / np.where(norms == 0, 1.0, norms)
        return result

    async def aembed(
        self,
        texts: list[str],
        *,
        is_query: bool = False,
        batch_size: int | None = None,
        normalize: bool = True,
        concurrency: int = 5,
    ) -> np.ndarray:
        """Embed texts asynchronously via API, batching and processing concurrently.

        Args:
            texts: List of strings to embed.
            is_query: True for query-side task type.
            batch_size: Override default provider batch size.
            normalize: L2-normalize embeddings (recommended for cosine similarity).
            concurrency: Max concurrent HTTP requests.

        Returns:
            NumPy array of shape ``(len(texts), embed_dim)``.
        """
        import httpx  # noqa: PLC0415

        bs = batch_size or self._batch_size
        chunks = [texts[i : i + bs] for i in range(0, len(texts), bs)]

        semaphore = asyncio.Semaphore(concurrency)

        async def worker(client: httpx.AsyncClient, chunk: list[str]) -> np.ndarray:
            async with semaphore:
                if self.provider == "openrouter":
                    return await self._aembed_batch_openrouter(client, chunk)
                return await self._aembed_batch_jina(client, chunk, is_query=is_query)

        async with httpx.AsyncClient(timeout=60.0) as client:
            tasks = [worker(client, chunk) for chunk in chunks]
            parts = await asyncio.gather(*tasks)

        result = np.vstack(parts)
        if normalize:
            norms = np.linalg.norm(result, axis=1, keepdims=True)
            result = result / np.where(norms == 0, 1.0, norms)
        return result

    def embed_single(self, text: str, *, is_query: bool = False) -> np.ndarray:
        """Embed a single text string."""
        return self.embed([text], is_query=is_query)[0]

    @property
    def embedding_dim(self) -> int:
        """Return the embedding vector dimension."""
        return self._embed_dim

    @property
    def tokens_used(self) -> int:
        """Total tokens consumed in this session (Jina only)."""
        return self._tokens_used

    @property
    def token_budget_remaining(self) -> int | None:
        """Remaining tokens in the free-tier budget, or None if unlimited."""
        if self._token_budget is None:
            return None
        return max(0, self._token_budget - self._tokens_used)
