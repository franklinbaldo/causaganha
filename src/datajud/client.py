"""HTTP client for the DataJud public API (CNJ) — one ES index per tribunal.

Endpoint: ``POST {BASE_URL}/api_publica_{sigla}/_search``.

Traps handled here (mapped in production by the owner's CLI client):

- **Two rate-limit flavors**: HTTP 429 at the gateway AND HTTP 200 with
  ``es_rejected_execution_exception`` in the body (the ES search queue is
  full). Both are transient → retry with exponential backoff. An exhausted
  retry budget raises :class:`DataJudRateLimitError` — a 200-with-rejection
  is NEVER treated as success.
- ``track_total_hits: true`` always (otherwise totals saturate at 10000).
- Textual fields need ``.keyword`` in sort/term/agg (the raw field is
  ``text`` and returns HTTP 400).
- HTTP 401 → :class:`DataJudAuthError` with rotation instructions. Production
  and CI usage can override the configured public default via the ``DATAJUD_API_KEY`` env var.
- Batch CNJ lookup (``terms`` on ``numeroProcesso``, paginated) — never one
  request per CNJ. Internal rate limiting (aiolimiter) plus a pause between
  batches keeps the CNJ's ES queue happy.
"""

from __future__ import annotations

import asyncio
import os
from itertools import batched
from typing import TYPE_CHECKING, Self

import httpx
import structlog
import tenacity
from aiolimiter import AsyncLimiter

from causaganha.config import DATAJUD_PUBLIC_API_KEY_DEFAULT
from datajud.models import normalizar_cnj


if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import TracebackType


log = structlog.get_logger()

BASE_URL = "https://api-publica.datajud.cnj.jus.br"

API_KEY_ENV = "DATAJUD_API_KEY"
WIKI_ACESSO_URL = "https://datajud-wiki.cnj.jus.br/api-publica/acesso/"

DEFAULT_TRIBUNAL = "tjro"
_UA = "causaganha/datajud (+https://github.com/franklinbaldo/causaganha)"

HTTP_UNAUTHORIZED = 401
HTTP_TOO_MANY_REQUESTS = 429

# Capa fields fetched by default — avoids pulling the (potentially huge)
# movimentos array when only the capa is needed.
CAPA_SOURCE_FIELDS: tuple[str, ...] = (
    "numeroProcesso",
    "classe",
    "assuntos",
    "orgaoJulgador",
    "grau",
    "sistema",
    "formato",
    "dataAjuizamento",
    "dataHoraUltimaAtualizacao",
    "nivelSigilo",
    "tribunal",
)

# Aggregation dimensions → ES fields. Textual fields MUST use ``.keyword``.
FACET_FIELDS: dict[str, str] = {
    "classe": "classe.nome.keyword",
    "assunto": "assuntos.nome.keyword",
    "orgao": "orgaoJulgador.nome.keyword",
    "grau": "grau.keyword",
    "sistema": "sistema.nome.keyword",
}


class DataJudError(RuntimeError):
    """Base error for DataJud client failures."""


class DataJudAuthError(DataJudError):
    """Missing/rejected DataJud API key or a key rotated by the CNJ."""


class DataJudRateLimitError(DataJudError):
    """Both rate-limit flavors persisted beyond the retry budget."""


class _TransientRejectionError(Exception):
    """Internal marker for retriable rejections (HTTP 429 or ES rejection)."""


def get_api_key() -> str:
    """Return the DataJud API key from env or the configured public default.

    ``DATAJUD_API_KEY`` is the rotation override for CI/production. The fallback
    lives in ``causaganha.config`` with the committed key history documented in
    ``docs/datajud-api-keys.md``.
    """
    return os.environ.get(API_KEY_ENV, "").strip() or DATAJUD_PUBLIC_API_KEY_DEFAULT


def search_endpoint(tribunal: str) -> str:
    """Search URL for a tribunal index (e.g. ``api_publica_tjro``)."""
    return f"{BASE_URL}/api_publica_{tribunal.lower()}/_search"


def is_es_rejection(payload: object) -> bool:
    """True when an HTTP 200 body carries an ES queue-full rejection.

    Status code is not a verdict — the rejection arrives inside a 200 body as
    ``{"error": {"root_cause": [{"type": "es_rejected_execution_exception"}]}}``.
    """
    if not isinstance(payload, dict) or "error" not in payload:
        return False
    error = payload.get("error")
    if not isinstance(error, dict):
        return False
    root_cause = error.get("root_cause", [])
    if not isinstance(root_cause, list):
        return False
    return any(
        "rejected_execution" in cause.get("type", "")
        for cause in root_cause
        if isinstance(cause, dict)
    )


def is_es_error(payload: object) -> bool:
    """True when an HTTP 200 body carries ANY Elasticsearch error.

    Status code is not a verdict (see :func:`is_es_rejection`): a 200 can
    still carry ``{"error": {...}}`` for non-transient failures too (e.g.
    ``query_shard_exception``, a malformed query). Those are NOT retried —
    only the queue-full flavor is — but they must never be silently treated
    as a normal (empty) result either.
    """
    return isinstance(payload, dict) and "error" in payload


def retry_wait(backoff_base: float) -> tenacity.wait_exponential:
    """Exponential backoff (base doubling, capped at 30s) for both flavors."""
    return tenacity.wait_exponential(multiplier=backoff_base, max=30)


class DataJudClient:
    """Async client for one tribunal index, with retry, rate limit and batching.

    Use as an async context manager::

        async with DataJudClient(tribunal="tjro") as client:
            sources = await client.fetch_processos(cnjs)
    """

    def __init__(
        self,
        tribunal: str = DEFAULT_TRIBUNAL,
        api_key: str | None = None,
        *,
        timeout: float = 90.0,
        max_retries: int = 5,
        backoff_base: float = 2.0,
        requests_per_minute: int = 30,
        batch_size: int = 50,
        batch_pause: float = 1.0,
        page_size: int = 500,
    ) -> None:
        """Configure the client; the HTTP session opens on ``__aenter__``."""
        self.tribunal = tribunal.lower()
        self._api_key = api_key or get_api_key()
        self._endpoint = search_endpoint(self.tribunal)
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._batch_size = batch_size
        self._batch_pause = batch_pause
        self._page_size = page_size
        self._limiter = AsyncLimiter(requests_per_minute, 60)
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        """Open the underlying HTTP session."""
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"APIKey {self._api_key}",
                "User-Agent": _UA,
            },
        )
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        """Close the underlying HTTP session."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            msg = "DataJudClient must be used as an async context manager"
            raise RuntimeError(msg)
        return self._client

    # ── Low-level search with retry ──────────────────────────────────────

    async def search(self, body: dict) -> dict:
        """POST *body* to the tribunal index, retrying both rate-limit flavors.

        Raises :class:`DataJudRateLimitError` when the retry budget is
        exhausted, :class:`DataJudAuthError` on 401 (no retry) and the usual
        httpx errors for other failures.
        """
        try:
            async for attempt in tenacity.AsyncRetrying(
                stop=tenacity.stop_after_attempt(self._max_retries + 1),
                wait=retry_wait(self._backoff_base),
                retry=tenacity.retry_if_exception_type(
                    (_TransientRejectionError, httpx.TransportError, httpx.TimeoutException)
                ),
                reraise=True,
            ):
                with attempt:
                    return await self._search_once(body)
        except _TransientRejectionError as exc:
            msg = f"DataJud rate limit persisted after {self._max_retries + 1} attempts: {exc}"
            raise DataJudRateLimitError(msg) from exc
        msg = "unreachable"
        raise RuntimeError(msg)  # pragma: no cover

    async def _search_once(self, body: dict) -> dict:
        async with self._limiter:
            resp = await self._http.post(self._endpoint, json=body)
        _raise_for_status_flavor(resp)
        payload = resp.json()
        if is_es_rejection(payload):
            log.warning("datajud_es_rejection", tribunal=self.tribunal)
            msg = "es_rejected_execution_exception (ES search queue full)"
            raise _TransientRejectionError(msg)
        if is_es_error(payload):
            log.error("datajud_es_error", tribunal=self.tribunal, error=payload.get("error"))
            msg = f"DataJud returned an Elasticsearch error in HTTP 200: {payload.get('error')}"
            raise DataJudError(msg)
        return payload

    # ── Batch CNJ lookup ─────────────────────────────────────────────────

    async def fetch_processos(self, cnjs: Sequence[str]) -> list[dict]:
        """Fetch capa + movimentos for a list of CNJs (all graus).

        CNJs are normalized to 20 digits, deduplicated and queried in
        batches via a ``terms`` query on ``numeroProcesso`` — never one
        request per CNJ. Returns the raw ``_source`` dicts.
        """
        unique = _normalize_cnjs(cnjs)
        sources: list[dict] = []
        for index, batch in enumerate(batched(unique, self._batch_size)):
            if index and self._batch_pause:
                await asyncio.sleep(self._batch_pause)
            sources.extend(await self._fetch_batch(list(batch)))
        log.info(
            "datajud_fetch_done",
            tribunal=self.tribunal,
            cnjs=len(unique),
            documentos=len(sources),
        )
        return sources

    async def _fetch_batch(self, batch: list[str]) -> list[dict]:
        out: list[dict] = []
        offset = 0
        while True:
            body = {
                "size": self._page_size,
                "from": offset,
                "track_total_hits": True,
                "query": {"terms": {"numeroProcesso": batch}},
                "sort": ["_doc"],
            }
            payload = await self.search(body)
            hits = payload.get("hits", {}).get("hits", [])
            out.extend(hit.get("_source", {}) for hit in hits)
            if len(hits) < self._page_size:
                return out
            offset += self._page_size

    # ── Aggregations ─────────────────────────────────────────────────────

    async def facetas(self, por: str, *, limite: int = 15) -> tuple[int, list[dict]]:
        """Aggregate the index by *por* (see FACET_FIELDS).

        Returns ``(total, buckets)`` where each bucket is
        ``{"chave": str, "qtd": int}``.
        """
        field = FACET_FIELDS[por]
        body = {
            "size": 0,
            "track_total_hits": True,
            "query": {"match_all": {}},
            "aggs": {"facetas": {"terms": {"field": field, "size": limite}}},
        }
        payload = await self.search(body)
        total = payload.get("hits", {}).get("total", {}).get("value", 0)
        buckets = payload.get("aggregations", {}).get("facetas", {}).get("buckets", [])
        return total, [
            {"chave": bucket.get("key"), "qtd": bucket.get("doc_count", 0)} for bucket in buckets
        ]


def _raise_for_status_flavor(resp: httpx.Response) -> None:
    """Classify the response status into the client's error taxonomy."""
    if resp.status_code == HTTP_UNAUTHORIZED:
        msg = (
            "HTTP 401 from DataJud: the configured API key was rejected "
            f"or rotated by the CNJ. Fetch the current key at {WIKI_ACESSO_URL} "
            f"and set the {API_KEY_ENV} environment variable."
        )
        raise DataJudAuthError(msg)
    if resp.status_code == HTTP_TOO_MANY_REQUESTS:
        msg = "HTTP 429 (gateway rate limit)"
        raise _TransientRejectionError(msg)
    resp.raise_for_status()


def _normalize_cnjs(cnjs: Sequence[str]) -> list[str]:
    """Normalize to 20 digits, drop invalid, dedupe preserving order."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in cnjs:
        cnj = normalizar_cnj(raw)
        if cnj and cnj not in seen:
            seen.add(cnj)
            out.append(cnj)
    return out
