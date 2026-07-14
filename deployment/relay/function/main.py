"""HTTP relay: forwards a single request to an allowlisted destination host.

Built because Cloud Run functions (gen2, southamerica-east1) can reach both
scon.stj.jus.br and juris-back.tjro.jus.br with real content — validated in
Fase 0 with a throwaway probe function before this was written (GitHub
Actions runners are blocked; these serverless egress IPs are not, as of
2026-07-13). This is not an open proxy: only *.stj.jus.br and *.tjro.jus.br
are forwardable, and every request must carry a valid ``X-Relay-Token``.

Contract:
- Destination URL comes in the ``X-Relay-Url`` request header.
- Auth via ``X-Relay-Token`` (constant-time compare against the
  ``RELAY_TOKEN`` env var, sourced from Secret Manager at deploy time).
- Method, body and headers are forwarded as-is (minus hop-by-hop and
  ``X-Relay-*`` headers); ``Host`` is rewritten to the destination host.
- Redirects are NOT followed — the 3xx is returned to the caller, who
  decides whether to follow it back through the relay.
"""

from __future__ import annotations

import hmac
import logging
import os
import time
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import functions_framework
import httpx


if TYPE_CHECKING:
    from flask import Request, Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("relay")

_ALLOWED_SUFFIXES = (".stj.jus.br", ".tjro.jus.br")
_ALLOWED_EXACT = frozenset({"stj.jus.br", "tjro.jus.br"})

# Headers that must never be blindly forwarded: hop-by-hop headers (RFC 9110
# §7.6.1) plus Content-Length (httpx recomputes it from the body it sends)
# and Host (rewritten explicitly to the destination's host below).
_STRIP_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "content-length",
        "host",
    }
)

_RELAY_TOKEN = os.environ.get("RELAY_TOKEN", "")

# One shared client for the function instance's lifetime — connection reuse
# across warm invocations, same rationale as the repo's own tjro_juris client.
_client = httpx.Client(timeout=60, follow_redirects=False)


def _host_allowed(hostname: str | None) -> bool:
    """True if *hostname* is under the STJ/TJRO allowlist."""
    if not hostname:
        return False
    hostname = hostname.lower()
    return hostname in _ALLOWED_EXACT or hostname.endswith(_ALLOWED_SUFFIXES)


def _token_valid(request: Request) -> bool:
    """Constant-time check of ``X-Relay-Token`` against ``RELAY_TOKEN``."""
    supplied = request.headers.get("X-Relay-Token", "")
    if not _RELAY_TOKEN or not supplied:
        return False
    # Compare as bytes — hmac.compare_digest rejects non-ASCII str inputs,
    # and header values may arrive latin-1-decoded by werkzeug.
    return hmac.compare_digest(supplied.encode("utf-8"), _RELAY_TOKEN.encode("utf-8"))


def _forward_headers(request: Request, target_host: str) -> dict[str, str]:
    """Client headers minus hop-by-hop/``X-Relay-*``, with ``Host`` rewritten."""
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in _STRIP_HEADERS and not key.lower().startswith("x-relay-")
    }
    headers["Host"] = target_host
    return headers


@functions_framework.http
def relay(request: Request) -> Response | tuple[str, int] | tuple[bytes, int, dict[str, str]]:
    """Forward *request* to the host named in ``X-Relay-Url``, allowlist-checked."""
    if not _token_valid(request):
        return ("unauthorized", 401)

    target_url = request.headers.get("X-Relay-Url", "")
    parsed = urlparse(target_url)
    host_ok = _host_allowed(parsed.hostname)
    if not target_url or parsed.scheme not in ("http", "https") or not host_ok:
        return ("forbidden: destination host not in allowlist", 403)

    method = request.method
    body = request.get_data() or None
    headers = _forward_headers(request, parsed.hostname)

    start = time.monotonic()
    try:
        upstream = _client.request(method, target_url, headers=headers, content=body)
    except httpx.HTTPError as exc:
        logger.info(
            "relay_upstream_error method=%s host=%s error=%s elapsed_s=%.2f",
            method,
            parsed.hostname,
            type(exc).__name__,
            time.monotonic() - start,
        )
        return (f"upstream error: {type(exc).__name__}", 502)

    logger.info(
        "relay_ok method=%s host=%s status=%s elapsed_s=%.2f",
        method,
        parsed.hostname,
        upstream.status_code,
        time.monotonic() - start,
    )

    response_headers = {
        key: value for key, value in upstream.headers.items() if key.lower() not in _STRIP_HEADERS
    }
    return (upstream.content, upstream.status_code, response_headers)
