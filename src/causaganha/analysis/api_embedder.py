"""API-based embedding provider using Jina AI or Gemini.

Drops in as a replacement for LocalEmbedder — same interface, no GPU required.

Provider strategy (cheapest first)
----------------------------------
1. **Jina AI** (default) — ``jina-embeddings-v3``, 10 M free tokens/month.
   Set ``JINA_API_KEY``. Hard stops at budget to avoid surprise charges.
2. **Gemini on-demand** — ``gemini-embedding-exp-03-07``, $0.20/1M tokens.
   Set ``GEMINI_API_KEY``. Good fallback once Jina budget is consumed.
3. **Gemini Batch API** — same model but async JSONL job, **50 % discount**
   (≈ $0.10/1M tokens). Best for large offline corpora (up to 2 GB per job).
   Use :meth:`embed_batch_async` instead of :meth:`embed`.

Usage
-----
    # Jina (default)
    embedder = ApiEmbedder()                          # reads JINA_API_KEY
    vecs = embedder.embed(["Julgo procedente."], is_query=True)
    print(embedder.token_budget_remaining)            # tokens left this month

    # Gemini on-demand
    embedder = ApiEmbedder(provider="gemini")         # reads GEMINI_API_KEY

    # Gemini Batch (async, 50 % cheaper, up to 2 GB)
    import asyncio
    embedder = ApiEmbedder(provider="gemini")
    result = asyncio.run(embedder.embed_batch_async(texts, jsonl_path="/tmp/job.jsonl"))
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Literal

import numpy as np
import structlog

logger = structlog.get_logger()

Provider = Literal["gemini", "jina"]

# ---------------------------------------------------------------------------
# Provider constants
# ---------------------------------------------------------------------------

# Gemini embedding model (EmbeddingGemma-based, 8192-token context)
GEMINI_MODEL = "models/gemini-embedding-exp-03-07"
GEMINI_EMBED_DIM = 768           # default; also supports 1536 and 3072
GEMINI_BATCH_SIZE = 100          # texts per batchEmbedContents request
GEMINI_RPM_LIMIT = 1500          # free-tier requests-per-minute
GEMINI_PRICE_PER_1M = 0.20       # USD, on-demand
GEMINI_BATCH_PRICE_PER_1M = 0.10 # USD, Batch API (50 % discount)
GEMINI_BATCH_MAX_INPUT_BYTES = 2 * 1024 ** 3  # 2 GB per batch job

# Jina jina-embeddings-v3 (multilingual, PT-BR native)
JINA_MODEL = "jina-embeddings-v3"
JINA_EMBED_DIM = 1024
JINA_BATCH_SIZE = 128
JINA_ENDPOINT = "https://api.jina.ai/v1/embeddings"
JINA_RPM_LIMIT = 500          # free-tier RPM
JINA_FREE_TOKEN_BUDGET = 10_000_000   # 10M tokens/month free tier
JINA_TOKEN_WARN_THRESHOLD = 0.90      # warn at 90% consumed


class ApiEmbedder:
    """API-backed embedder — no GPU, no local model download.

    Args:
        provider: ``"gemini"`` or ``"jina"``.
        api_key: API key. Falls back to ``GEMINI_API_KEY`` / ``JINA_API_KEY``
            environment variables.
        truncate_dim: Optional MRL truncation (Gemini supports 256/512/768).
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
    ) -> None:
        self.provider = provider
        self.truncate_dim = truncate_dim

        if provider == "gemini":
            self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
            if not self._api_key:
                msg = "GEMINI_API_KEY not set. Get one at https://aistudio.google.com/app/apikey"
                raise ValueError(msg)
            self._batch_size = GEMINI_BATCH_SIZE
            self._rpm_limit = rpm_limit or GEMINI_RPM_LIMIT
            self._embed_dim = truncate_dim or GEMINI_EMBED_DIM
            self._token_budget: int | None = None
            self._tokens_used: int = 0
            self._init_gemini()

        elif provider == "jina":
            self._api_key = api_key or os.environ.get("JINA_API_KEY", "")
            if not self._api_key:
                msg = "JINA_API_KEY not set. Get one at https://jina.ai/?sui=apikey"
                raise ValueError(msg)
            self._batch_size = JINA_BATCH_SIZE
            self._rpm_limit = rpm_limit or JINA_RPM_LIMIT
            self._embed_dim = truncate_dim or JINA_EMBED_DIM
            self._token_budget = token_budget
            self._tokens_used = 0

        else:
            msg = f"Unknown provider: {provider!r}. Choose 'gemini' or 'jina'."
            raise ValueError(msg)

        self._request_times: list[float] = []
        logger.info(
            "api_embedder_init",
            provider=provider,
            embed_dim=self._embed_dim,
            rpm_limit=self._rpm_limit,
            token_budget=self._token_budget,
        )

    def _init_gemini(self) -> None:
        try:
            from google import genai  # noqa: PLC0415
        except ImportError as exc:
            msg = "google-genai is required: uv add google-genai"
            raise ImportError(msg) from exc
        self._genai_client = genai.Client(api_key=self._api_key)

    def _rate_limit(self) -> None:
        """Block until we are within the RPM limit (sliding 60-second window)."""
        now = time.monotonic()
        self._request_times = [t for t in self._request_times if now - t < 60.0]
        if len(self._request_times) >= self._rpm_limit:
            sleep_for = 60.0 - (now - self._request_times[0]) + 0.1
            if sleep_for > 0:
                logger.debug("api_rate_limit_sleep", seconds=round(sleep_for, 2))
                time.sleep(sleep_for)
        self._request_times.append(time.monotonic())

    # ------------------------------------------------------------------
    # Provider-specific batch embed
    # ------------------------------------------------------------------

    def _embed_batch_gemini(self, texts: list[str], *, is_query: bool) -> np.ndarray:
        from google.genai import types as gtypes  # noqa: PLC0415

        task_type = "RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT"
        config = gtypes.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=self.truncate_dim,  # None → full 768
        )
        self._rate_limit()
        response = self._genai_client.models.embed_content(
            model=GEMINI_MODEL,
            contents=texts,
            config=config,
        )
        return np.array(
            [e.values for e in response.embeddings], dtype=np.float32
        )

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
                    "Switch to provider='gemini' or get a new Jina API key."
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
        bs = batch_size or self._batch_size
        chunks = [texts[i : i + bs] for i in range(0, len(texts), bs)]
        parts: list[np.ndarray] = []

        for chunk in chunks:
            if self.provider == "gemini":
                emb = self._embed_batch_gemini(chunk, is_query=is_query)
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
    ) -> np.ndarray:
        """Async wrapper — runs synchronous embed in a thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.embed(
                texts, is_query=is_query, batch_size=batch_size, normalize=normalize
            ),
        )

    def embed_single(self, text: str, *, is_query: bool = False) -> np.ndarray:
        """Embed a single text string."""
        return self.embed([text], is_query=is_query)[0]

    @property
    def embedding_dim(self) -> int:
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

    # ------------------------------------------------------------------
    # Gemini Batch API (50 % cheaper, async, up to 2 GB per job)
    # ------------------------------------------------------------------

    async def embed_batch_async(
        self,
        texts: list[str],
        *,
        is_query: bool = False,
        normalize: bool = True,
        poll_interval: float = 10.0,
    ) -> np.ndarray:
        """Submit a Gemini Batch API job and wait for results.

        Uses the asynchronous Batch API (50 % discount vs on-demand).
        Ideal for large offline corpora — processes up to 2 GB per job.
        Only available when ``provider="gemini"``.

        Args:
            texts: List of strings to embed.
            is_query: True for query-side task type.
            normalize: L2-normalize output embeddings.
            poll_interval: Seconds between status checks while job runs.

        Returns:
            NumPy array of shape ``(len(texts), embed_dim)``.

        Raises:
            RuntimeError: If not using Gemini provider, or batch job fails.
        """
        if self.provider != "gemini":
            msg = "embed_batch_async is only available for provider='gemini'."
            raise RuntimeError(msg)

        import json as _json  # noqa: PLC0415
        import tempfile  # noqa: PLC0415

        from google.genai import types as gtypes  # noqa: PLC0415

        task_type = "RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT"

        # Build JSONL request file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as tmp:
            for i, text in enumerate(texts):
                record = {
                    "key": str(i),
                    "request": {
                        "model": GEMINI_MODEL,
                        "contents": [{"parts": [{"text": text}]}],
                        "generationConfig": {
                            "taskType": task_type,
                            **(
                                {"outputDimensionality": self.truncate_dim}
                                if self.truncate_dim
                                else {}
                            ),
                        },
                    },
                }
                tmp.write(_json.dumps(record, ensure_ascii=False) + "\n")
            jsonl_path = tmp.name

        logger.info(
            "gemini_batch_upload",
            n_texts=len(texts),
            jsonl_path=jsonl_path,
            estimated_cost_usd=round(
                sum(len(t) / 4 / 1_000_000 * GEMINI_BATCH_PRICE_PER_1M for t in texts),
                4,
            ),
        )

        # Upload the JSONL file
        uploaded = self._genai_client.files.upload(
            path=jsonl_path,
            config=gtypes.UploadFileConfig(mime_type="application/jsonl"),
        )

        # Submit batch job
        batch_job = self._genai_client.batches.create(
            model=GEMINI_MODEL,
            src=uploaded.name,
            config=gtypes.CreateBatchJobConfig(
                dest=f"batches/causaganha-embeddings-{int(time.time())}"
            ),
        )
        logger.info("gemini_batch_submitted", job_name=batch_job.name)

        # Poll until complete
        while batch_job.state not in ("JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED"):
            await asyncio.sleep(poll_interval)
            batch_job = self._genai_client.batches.get(name=batch_job.name)
            logger.debug("gemini_batch_status", state=batch_job.state, name=batch_job.name)

        if batch_job.state == "JOB_STATE_FAILED":
            msg = f"Gemini Batch job failed: {batch_job.error}"
            raise RuntimeError(msg)

        # Collect results (ordered by key)
        rows: dict[int, list[float]] = {}
        for response in self._genai_client.batches.list_job_results(name=batch_job.name):
            key = int(response.key)
            embedding = response.response.embedding.values
            rows[key] = embedding

        result = np.array([rows[i] for i in range(len(texts))], dtype=np.float32)
        if normalize:
            norms = np.linalg.norm(result, axis=1, keepdims=True)
            result = result / np.where(norms == 0, 1.0, norms)

        logger.info(
            "gemini_batch_complete",
            shape=result.shape,
            job_name=batch_job.name,
        )
        return result

