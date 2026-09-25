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
- Destination URL comes in the ``X-Relay-Url`` request header, and must be
  ``https://`` — plaintext ``http://`` is rejected even to an allowlisted
  host (TM-02 / #1609).
- Auth via ``X-Relay-Token`` (constant-time compare against the
  ``RELAY_TOKEN`` env var, sourced from Secret Manager at deploy time).
- Method is restricted to ``GET``/``HEAD``/``POST`` — the only verbs the
  real STJ/TJRO/TSE crawlers use; anything else is ``405``.
- Body and headers are forwarded, minus hop-by-hop headers, ``X-Relay-*``
  headers, and ``Authorization``/``Cookie`` (never legitimately needed by a
  caller through this relay); ``Host`` is rewritten to the destination
  host, and the upstream's ``Set-Cookie`` is never forwarded back.
- Request bodies above ``_MAX_REQUEST_BODY_BYTES`` are rejected (``413``);
  upstream responses above ``_MAX_RESPONSE_BYTES`` are aborted mid-stream
  (``502``) rather than fully buffered.
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

# Headers that must never be blindly forwarded: hop-by-hop headers (RFC 9110
# §7.6.1), Content-Length (httpx recomputes it from the body it sends), Host
# (rewritten explicitly to the destination's host below), and Authorization/
# Cookie — no caller through this relay authenticates to STJ/TJRO/TSE with
# either (auth is X-Relay-Token to the relay itself), so forwarding them
# would only leak a caller's own credentials to whatever host the allowlist
# permits (TM-02 / #1609).
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
        "authorization",
        "cookie",
    }
)

# httpx's client transparently gunzips the upstream response into
# `.content` — the bytes we return are already decoded. Forwarding the
# upstream's original Content-Encoding header alongside that decoded body
# makes the CALLER's httpx try to gunzip it a second time and raise
# DecodingError. Response-only: request-side Content-Encoding (basically
# never sent by these crawlers) is left alone.
#
# Set-Cookie is also response-only: no upstream in the allowlist is a
# session-bearing site the caller should start trusting cookies from, and
# forwarding it would let a compromised relay plant cookies in the caller.
_RESPONSE_STRIP_HEADERS = _STRIP_HEADERS | {"content-encoding", "set-cookie"}

# Methods the real crawlers use (STJ CKAN GET, TJRO Elasticsearch POST) plus
# HEAD for parity — see deployment/relay/README.md. Not an open proxy: a
# stolen token must not be able to replay mutating verbs against tribunal
# hosts.
_ALLOWED_METHODS = frozenset({"GET", "HEAD", "POST"})

# TM-02 / #1609: a relay with no budget lets a stolen token or misbehaving
# upstream exhaust the function instance's memory. These are generous
# (real DJEN/STJ/TJRO payloads are small JSON/HTML documents) but bounded.
_MAX_REQUEST_BODY_BYTES = 10 * 1024 * 1024  # 10 MiB
_MAX_RESPONSE_BYTES = 25 * 1024 * 1024  # 25 MiB

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

    method = request.method
    if method not in _ALLOWED_METHODS:
        return ("method not allowed", 405)

    target_url = request.headers.get("X-Relay-Url", "")
    parsed = urlparse(target_url)
    host_ok = _host_allowed(parsed.hostname)
    if not target_url or parsed.scheme != "https" or not host_ok:
        return ("forbidden: destination host not in allowlist", 403)

    body = request.get_data() or None
    if body is not None and len(body) > _MAX_REQUEST_BODY_BYTES:
        return ("request body too large", 413)

    headers = _forward_headers(request, parsed.hostname)

    start = time.monotonic()
    try:
        with _client.stream(method, target_url, headers=headers, content=body) as upstream:
            chunks: list[bytes] = []
            received = 0
            for chunk in upstream.iter_bytes():
                received += len(chunk)
                if received > _MAX_RESPONSE_BYTES:
                    logger.info(
                        "relay_response_too_large method=%s host=%s elapsed_s=%.2f",
                        method,
                        parsed.hostname,
                        time.monotonic() - start,
                    )
                    return ("upstream response too large", 502)
                chunks.append(chunk)
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

    return (b"".join(chunks), status_code, response_headers)
