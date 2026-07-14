"""JURIS TJRO HTTP client — search and aggregations.

API contract (reverse-engineered from the portal's Next.js bundles, 2026-07):

- ``POST /search/varios_parametros/`` with body
  ``{"from": N, "size": M, "fields": {...}, "sort": [...]}``.
  Filters live under ``fields`` using Elasticsearch ``.raw`` keyword subfields
  (``tipo.raw``, ``ds_classe_judicial.raw``, ...). Free text goes in
  ``fields.query``; date range in ``fields.dtjulgamento_inicio`` /
  ``fields.dtjulgamento_fim`` (ISO ``YYYY-MM-DD``, inclusive).
  The old flat body (``{"token": "", "tipo": [...], "texto": ...}``) now
  returns HTTP 500.
- ``POST /search/agregacoes`` with body ``{"fields": {...}}`` (GET is 405).
  Aggregations honor ``tipo.raw`` but NOT the ``dtjulgamento_*`` date window
  (date-filtered aggregation requests return empty buckets — verified live
  2026-07-12).
- Pagination is capped by the Elasticsearch result window:
  ``from + size`` must stay <= ``MAX_RESULT_WINDOW`` (10 000) or the server
  returns HTTP 500. Callers that need more must slice by date window.
"""

from __future__ import annotations

import html as htmllib
import random
import re
import time
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import httpx
import structlog

from common.relay import relay_transport_from_env


if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import NoReturn

log = structlog.get_logger()

TIPOS = [
    "ACÓRDÃO",
    "DECISÃO",
    "DECISÃO DA PRESIDÊNCIA",
    "SENTENÇA",
    "VOTO",
    "EMENTA",
    "RELATÓRIO",
]

ENDPOINT = "https://juris-back.tjro.jus.br/search/varios_parametros/"
AGGREGATIONS_ENDPOINT = "https://juris-back.tjro.jus.br/search/agregacoes"
PAGE_SIZE = 400

# Elasticsearch max_result_window: requests with from + size beyond this 500.
MAX_RESULT_WINDOW = 10_000

MAX_ATTEMPTS = 4
_BASE_DELAY_S = 2.0
_HTTP_SERVER_ERROR = 500

# TJRO's STIC anti-abuse system blocks an offending IP by returning HTTP 200
# with an HTML "Página Bloqueada" page instead of the expected JSON — observed
# live (2026-07-14) after ~10h of sustained crawling from one machine during
# the historical backfill. A bare `resp.json()` on this body raised an opaque
# JSONDecodeError instead of a diagnosable error, and crashed several years'
# worth of crawl near-instantly (indistinguishable from a random transient
# blip) before this was caught.
_BLOCKED_PAGE_MARKER = "Página Bloqueada"


class JurisBlockedError(RuntimeError):
    """TJRO's STIC anti-abuse system blocked this network's IP.

    Never retried automatically (see ``_post_checked``) — this is an IP-level
    block with an unknown cooldown, not a transient blip; blindly retrying
    just wastes requests against a wall. Route through ``common.relay``
    (``RELAY_URL``/``RELAY_TOKEN``) from a different network instead.
    """


_UA = "Mozilla/5.0 (causaganha/tjro-juris)"
_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": _UA,
}

# Crawl-stable TOTAL ordering: newest first, score, then the unique document
# id as the final tiebreaker. Without a unique key the (dtjulgamento, _score)
# pair is not a total order — same-day/same-score docs can shuffle between
# ``from`` pages, producing duplicates and omissions. The backend accepts
# ``id_processo_documento`` as a sort key (verified live 2026-07-12: each
# hit's ``sort`` array carries the id as its third value and ties order by it).
_SORT_RECENT = [
    {"dtjulgamento": "desc"},
    {"_score": "desc"},
    {"id_processo_documento": "asc"},
]

# One shared client for the whole crawl: connection reuse (keep-alive) makes a
# multi-thousand-request crawl far less likely to hit connect timeouts than
# opening a fresh TCP+TLS handshake per request.
#
# transport routes through the relay (see common.relay) when RELAY_URL/
# RELAY_TOKEN are set — used in CI, where runner egress ConnectTimeouts on
# juris-back.tjro.jus.br. Direct connection otherwise (local/dev default).
_CLIENT = httpx.Client(
    timeout=30,
    headers=_HEADERS,
    limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
    transport=relay_transport_from_env(),
)


def _sleep(seconds: float) -> None:
    """Sleep indirection so tests can patch the backoff away."""
    time.sleep(seconds)


def _backoff_delay(attempt: int) -> float:
    """Exponential backoff (2s, 4s, 8s, ...) with up to 25% jitter."""
    base = _BASE_DELAY_S * (2**attempt)
    return base * (1.0 + random.uniform(0.0, 0.25))  # noqa: S311 — jitter, not crypto


def _raise_last(last_exc: httpx.HTTPError) -> NoReturn:
    raise last_exc


def _retrying[T](op: Callable[[], T], url: str, *, max_attempts: int = MAX_ATTEMPTS) -> T:
    """Run *op*, retrying transport errors and 5xx with exponential backoff.

    Mirrors ``stj_acordaos.client._retrying`` (kept local — no cross-package
    imports). Retriable: ``httpx.TransportError`` (connect timeouts, resets)
    and HTTP 5xx. Anything else — notably 403 (WAF/rate-limit: back off, do
    not hammer) and 4xx contract errors — raises immediately. A persistent
    5xx still raises after the final attempt (the contract-break symptom).
    """
    last_exc: httpx.HTTPError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            result = op()
        except httpx.TransportError as exc:
            last_exc = exc
            log.warning("juris_transport_error", url=url, attempt=attempt, error=str(exc))
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code < _HTTP_SERVER_ERROR:
                raise
            last_exc = exc
            log.warning(
                "juris_retriable_status",
                url=url,
                attempt=attempt,
                status=exc.response.status_code,
            )
        else:
            return result
        if attempt < max_attempts:
            delay = _backoff_delay(attempt - 1)
            log.info("juris_retry_backoff", url=url, attempt=attempt, sleep_s=round(delay, 1))
            _sleep(delay)
    if last_exc is None:  # pragma: no cover
        msg = "unreachable"
        raise RuntimeError(msg)
    _raise_last(last_exc)


def _post_checked(url: str, body: dict) -> dict:
    """POST *body* to *url* on the shared client; raise for error statuses.

    Raises :class:`JurisBlockedError` — not retried — when the response is a
    200 carrying TJRO's STIC block page instead of JSON.
    """
    resp = _CLIENT.post(url, json=body)
    resp.raise_for_status()
    if _BLOCKED_PAGE_MARKER in resp.text[:2000]:
        msg = (
            f"JURIS blocked: HTTP 200 but body is TJRO's STIC block page, not "
            f"JSON, from {url}. This network's IP has been blocked by TJRO's "
            "anti-abuse system — not a transient blip. Route through "
            "common.relay (RELAY_URL/RELAY_TOKEN) from a different network."
        )
        raise JurisBlockedError(msg)
    return resp.json()


def clean_html(html: str) -> str:
    """Remove base64 img tags, style, script blocks, all HTML tags, decode HTML entities."""
    if not html:
        return ""
    html = re.sub(r"<img[^>]*>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style[^>]*>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<script[\s\S]*?</script[^>]*>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<[^>]+>", " ", html)
    html = htmllib.unescape(html)
    return re.sub(r"\s+", " ", html).strip()


def search(
    tipo: str,
    from_: int = 0,
    size: int = PAGE_SIZE,
    texto: str = "",
    *,
    date_start: str | None = None,
    date_end: str | None = None,
    extra_fields: dict | None = None,
) -> dict:
    """POST to the JURIS search endpoint.

    ``tipo`` is sent as ``fields["tipo.raw"]`` and MUST be wrapped in a list.
    ``texto`` maps to ``fields.query`` (free text). ``date_start`` /
    ``date_end`` are inclusive ISO dates mapped to ``dtjulgamento_inicio`` /
    ``dtjulgamento_fim``. ``extra_fields`` merges additional ``fields``
    filters (e.g. ``{"ds_orgao_julgador.raw": ["..."]}``) for sub-window
    slicing. Response is raw Elasticsearch (``hits.hits``).

    Transport errors and 5xx are retried with backoff; persistent failures
    raise. 403 raises immediately (WAF/rate-limit — never retry blindly,
    never treat as absent).
    """
    fields: dict = {"tipo.raw": [tipo]}
    if texto:
        fields["query"] = texto
    if date_start:
        fields["dtjulgamento_inicio"] = date_start
    if date_end:
        fields["dtjulgamento_fim"] = date_end
    if extra_fields:
        fields.update(extra_fields)

    body: dict = {
        "from": from_,
        "size": size,
        "fields": fields,
        "sort": _SORT_RECENT,
    }

    log.debug("juris_search", tipo=tipo, from_=from_, size=size, date_start=date_start)
    return _retrying(lambda: _post_checked(ENDPOINT, body), ENDPOINT)


def get_aggregations(fields: dict | None = None) -> dict:
    """POST to the JURIS aggregations endpoint (GET returns 405).

    ``fields`` narrows the aggregation scope (e.g. ``{"tipo.raw": ["VOTO"]}``).
    Note: the backend ignores ``dtjulgamento_*`` here (returns empty buckets),
    so date-windowed aggregations are NOT available.
    """
    body = {"fields": fields or {}}
    return _retrying(lambda: _post_checked(AGGREGATIONS_ENDPOINT, body), AGGREGATIONS_ENDPOINT)


PORTAL_URL = "https://juris.tjro.jus.br/jurisprudencia/"


def doc_url(
    id_processo_documento: int | str | None,
    *,
    sistema_origem: str = "",
    tipo: str = "",
    id_documento_principal: int | str | None = None,
) -> str:
    """Build portal URL with all required query parameters."""
    if id_processo_documento is None:
        return ""
    params: dict[str, str] = {"id": str(id_processo_documento)}
    if sistema_origem:
        params["sistema_origem"] = sistema_origem
    if tipo:
        params["tipo"] = tipo
    if id_documento_principal is not None:
        params["id_documento_principal"] = str(id_documento_principal)
    return f"{PORTAL_URL}?{urlencode(params)}"
