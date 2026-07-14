"""httpx transport that routes requests through the causaganha relay.

GitHub-hosted runners are blocked by the STJ WAF (``STJWAFBlockedError``) and
time out connecting to ``juris-back.tjro.jus.br`` — but a Cloud Run function
in ``southamerica-east1`` reaches both with real content (validated live,
2026-07-13; see ``deployment/relay/``). Serverless platforms don't support
proxy ``CONNECT``, so this routes traffic via a custom transport instead of
``HTTPS_PROXY``: the transport swaps the request's URL for the relay
function's URL, and moves the original destination into the ``X-Relay-Url``
header for the relay to forward to.

Activated purely by env (``RELAY_URL`` + ``RELAY_TOKEN``); if either is
unset, callers get ``None`` back and fall through to a direct connection —
zero behavior change for local/dev runs that don't opt in.
"""

from __future__ import annotations

import os

import httpx


_RELAY_URL_ENV = "RELAY_URL"
_RELAY_TOKEN_ENV = "RELAY_TOKEN"  # noqa: S105 — env var name, not a credential


def _relay_env() -> tuple[str, str] | None:
    url = os.environ.get(_RELAY_URL_ENV)
    token = os.environ.get(_RELAY_TOKEN_ENV)
    if not url or not token:
        return None
    return url, token


def _build_relayed_request(
    request: httpx.Request, relay_url: str, relay_token: str
) -> httpx.Request:
    """Rebuild *request* targeting the relay, original URL/token in headers."""
    headers = httpx.Headers(request.headers)
    headers["X-Relay-Url"] = str(request.url)
    headers["X-Relay-Token"] = relay_token
    # Recompute Host for the relay's own hostname — otherwise the relay's
    # HTTP server sees a Host header for the original destination.
    headers["host"] = httpx.URL(relay_url).host
    return httpx.Request(
        method=request.method,
        url=relay_url,
        headers=headers,
        stream=request.stream,
        extensions=request.extensions,
    )


class RelayTransport(httpx.BaseTransport):
    """Synchronous transport that forwards every request through the relay."""

    def __init__(
        self,
        relay_url: str,
        relay_token: str,
        *,
        inner: httpx.BaseTransport | None = None,
    ) -> None:
        """Wrap *inner* (default: a real ``httpx.HTTPTransport``) with relay rewriting."""
        self._relay_url = relay_url
        self._relay_token = relay_token
        self._inner = inner or httpx.HTTPTransport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Rewrite *request* to the relay and delegate to the inner transport."""
        relayed = _build_relayed_request(request, self._relay_url, self._relay_token)
        return self._inner.handle_request(relayed)

    def close(self) -> None:
        """Close the inner transport."""
        self._inner.close()


class AsyncRelayTransport(httpx.AsyncBaseTransport):
    """Async counterpart of :class:`RelayTransport`."""

    def __init__(
        self,
        relay_url: str,
        relay_token: str,
        *,
        inner: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Wrap *inner* (default: a real ``httpx.AsyncHTTPTransport``) with relay rewriting."""
        self._relay_url = relay_url
        self._relay_token = relay_token
        self._inner = inner or httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Rewrite *request* to the relay and delegate to the inner transport."""
        relayed = _build_relayed_request(request, self._relay_url, self._relay_token)
        return await self._inner.handle_async_request(relayed)

    async def aclose(self) -> None:
        """Close the inner transport."""
        await self._inner.aclose()


def relay_transport_from_env() -> RelayTransport | None:
    """Build a :class:`RelayTransport` from ``RELAY_URL``/``RELAY_TOKEN``, or ``None``."""
    env = _relay_env()
    return RelayTransport(*env) if env else None


def async_relay_transport_from_env() -> AsyncRelayTransport | None:
    """Build an :class:`AsyncRelayTransport` from env, or ``None`` if unset."""
    env = _relay_env()
    return AsyncRelayTransport(*env) if env else None
