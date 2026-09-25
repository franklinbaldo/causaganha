"""HTTP relay: forwards a single request to an allowlisted destination host.

Built because Cloud Run functions (gen2, southamerica-east1) can reach both
scon.stj.jus.br and juris-back.tjro.jus.br with real content — validated in
Fase 0 with a throwaway probe function before this was written (GitHub
Actions runners are blocked; these serverless egress IPs are not, as of
2026-07-13). This is not an open proxy: only *.stj.jus.br, *.tjro.jus.br and
*.tse.jus.br are forwardable, and every request must carry a valid
``X-Relay-Token``.

``*.tse.jus.br`` (issue #985) is not validated the same way yet: the block
observed there (an Akamai edgesuite.net 403 on cdn.tse.jus.br /
dadosabertos.tse.jus.br) is the same WAF-block *class* the relay bypasses
for STJ/TJRO, but nobody has redeployed this function with the wider
allowlist and confirmed live that this region's egress isn't Akamai-blocked
too. Confirm that before relying on it.

Contract:
- Destination URL comes in the ``X-Relay-Url`` request header and must be
  ``https``  — a stolen token must not be usable to route unencrypted
  traffic, and every real caller (tjro_juris/stj_acordaos/tse_processual,
  see ``src/common/relay.py``) only ever requests ``https``.
- Auth via ``X-Relay-Token`` (constant-time compare against the
  ``RELAY_TOKEN`` env var, sourced from Secret Manager at deploy time).
- Method is restricted to GET/HEAD/POST (the only methods any real caller
  uses — mirrors ``deployment/relay-cf``'s ``ALLOWED_METHODS``); body and
  headers are forwarded minus hop-by-hop, ``X-Relay-*`` and sensitive
  (``Authorization``/``Cookie``) headers — no real caller sends either, and
  forwarding them would let a stolen relay token also exfiltrate whatever
  credential the caller happened to be carrying. ``Host`` is rewritten to
  the destination host.
- Request body and upstream response are each capped (see
  ``MAX_REQUEST_BODY_BYTES``/``MAX_RESPONSE_BODY_BYTES``) so a misused
  token can't turn the relay into an unbounded egress/ingress amplifier.
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

_ALLOWED_SUFFIXES = (".stj.jus.br", ".tjro.jus.br", ".tse.jus.br")
_ALLOWED_EXACT = frozenset({"stj.jus.br", "tjro.jus.br", "tse.jus.br"})

# GET/HEAD/POST is every method any real caller uses (tjro_juris POSTs a
# search body, stj_acordaos/tse_processual GET) — mirrors relay-cf's own
# ALLOWED_METHODS so both relays share one minimal method policy (#1609).
_ALLOWED_METHODS = frozenset({"GET", "HEAD", "POST"})

# Headers a stolen relay token must never be able to smuggle through: no
# real caller sends either (grepped every src/*/client.py that routes
# through the relay), so stripping them unconditionally costs nothing and
# stops a leaked token from also exfiltrating an unrelated credential.
_SENSITIVE_HEADERS = frozenset({"authorization", "cookie"})

# Headers that must never be blindly forwarded: hop-by-hop headers (RFC 9110
# §7.6.1) plus Content-Length (httpx recomputes it from the body it sends),
# Host (rewritten explicitly to the destination's host below) and the
# sensitive headers above.
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
    | _SENSITIVE_HEADERS
)

# Budgets bounding how much a single relayed request/response can cost, so a
# stolen token or a misbehaving upstream can't turn the relay into an
# unbounded egress/ingress amplifier. Real traffic is small (tjro_juris's
# POST search body is a few hundred bytes of JSON; STJ/TJRO/TSE responses
# are JSON/HTML pages, not bulk downloads) — both budgets are generous
# multiples of that, not a tight fit.
MAX_REQUEST_BODY_BYTES = 5 * 1024 * 1024
MAX_RESPONSE_BODY_BYTES = 50 * 1024 * 1024

# httpx's client transparently gunzips the upstream response into
# `.content` — the bytes we return are already decoded. Forwarding the
# upstream's original Content-Encoding header alongside that decoded body
# makes the CALLER's httpx try to gunzip it a second time and raise
# DecodingError. Response-only: request-side Content-Encoding (basically
# never sent by these crawlers) is left alone.
_RESPONSE_STRIP_HEADERS = _STRIP_HEADERS | {"content-encoding"}

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

    if request.method not in _ALLOWED_METHODS:
        return ("method not allowed", 405)

    target_url = request.headers.get("X-Relay-Url", "")
    parsed = urlparse(target_url)
    host_ok = _host_allowed(parsed.hostname)
    if not target_url or parsed.scheme != "https" or not host_ok:
        return ("forbidden: destination host not in allowlist", 403)

    method = request.method
    body = request.get_data() or None
    if body and len(body) > MAX_REQUEST_BODY_BYTES:
        return ("request body too large", 413)
    headers = _forward_headers(request, parsed.hostname)

    start = time.monotonic()
    try:
        content = bytearray()
        with _client.stream(method, target_url, headers=headers, content=body) as upstream:
            for chunk in upstream.iter_bytes():
                content += chunk
                if len(content) > MAX_RESPONSE_BODY_BYTES:
                    logger.info(
                        "relay_response_too_large method=%s host=%s elapsed_s=%.2f",
                        method,
                        parsed.hostname,
                        time.monotonic() - start,
                    )
                    return ("upstream response exceeds size budget", 502)
            status_code = upstream.status_code
            response_headers = {
                key: value
                for key, value in upstream.headers.items()
                if key.lower() not in _RESPONSE_STRIP_HEADERS
            }
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
        status_code,
        time.monotonic() - start,
    )

    return (bytes(content), status_code, response_headers)
