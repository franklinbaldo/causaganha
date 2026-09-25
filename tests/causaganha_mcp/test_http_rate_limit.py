"""Per-client rate limiting for the public HTTP MCP transport (TM-06/#950).

`OperationalLimitsMiddleware` already bounds global concurrency and
per-call timeout (`tests/causaganha_mcp/test_http_transport.py`), but
nothing stops a single sequential caller from monopolizing that shared
budget and starving every other client -- docs/SECURITY_THREAT_MODEL.md
names this gap explicitly under TM-06. These tests exercise the
per-client-key rate limiter added to close it, using the same
`on_call_tool(context, call_next)` direct-call pattern as the existing
timeout/saturation tests (no real ASGI server needed).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import MiddlewareContext

import causaganha_mcp.http_server as http_entry
from causaganha_mcp.http_server import HttpSettings, OperationalLimitsMiddleware


if TYPE_CHECKING:
    pass


class _FakeClient:
    def __init__(self, host: str | None) -> None:
        self.host = host


class _FakeRequest:
    """Minimal stand-in for `starlette.requests.Request` -- only the
    attributes `OperationalLimitsMiddleware` reads: headers and client.
    """

    def __init__(self, *, client_host: str | None, headers: dict[str, str] | None = None) -> None:
        self._headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.client = _FakeClient(client_host)

    @property
    def headers(self) -> dict[str, str]:
        return self._headers


async def _noop_call(_context: MiddlewareContext) -> str:
    return "ok"


def _patch_request(monkeypatch: pytest.MonkeyPatch, request: _FakeRequest | None) -> None:
    def fake_get_http_request() -> _FakeRequest:
        if request is None:
            msg = "no request"
            raise RuntimeError(msg)
        return request

    monkeypatch.setattr(http_entry, "get_http_request", fake_get_http_request)


# ── HttpSettings ────────────────────────────────────────────────────────


def test_http_settings_default_rate_limit_is_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CAUSAGANHA_MCP_RATE_LIMIT_PER_MINUTE", raising=False)

    settings = HttpSettings.from_env()

    assert settings.rate_limit_per_minute is not None
    assert settings.rate_limit_per_minute > 0


def test_http_settings_rate_limit_zero_disables_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAUSAGANHA_MCP_RATE_LIMIT_PER_MINUTE", "0")

    settings = HttpSettings.from_env()

    assert settings.rate_limit_per_minute is None


def test_http_settings_reject_invalid_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAUSAGANHA_MCP_RATE_LIMIT_PER_MINUTE", "not-a-number")

    with pytest.raises(ValueError, match="CAUSAGANHA_MCP_RATE_LIMIT_PER_MINUTE"):
        HttpSettings.from_env()


def test_http_settings_reject_negative_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAUSAGANHA_MCP_RATE_LIMIT_PER_MINUTE", "-1")

    with pytest.raises(ValueError, match="CAUSAGANHA_MCP_RATE_LIMIT_PER_MINUTE"):
        HttpSettings.from_env()


# ── OperationalLimitsMiddleware rate limiting ─────────────────────────────


async def test_rate_limit_rejects_client_past_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_request(monkeypatch, _FakeRequest(client_host="203.0.113.5"))
    limits = OperationalLimitsMiddleware(
        timeout_seconds=5, max_concurrency=10, rate_limit_per_minute=2
    )

    assert await limits.on_call_tool(cast(MiddlewareContext, None), _noop_call) == "ok"
    assert await limits.on_call_tool(cast(MiddlewareContext, None), _noop_call) == "ok"
    with pytest.raises(ToolError, match="limite de chamadas"):
        await limits.on_call_tool(cast(MiddlewareContext, None), _noop_call)


async def test_rate_limit_is_scoped_per_client_key(monkeypatch: pytest.MonkeyPatch) -> None:
    limits = OperationalLimitsMiddleware(
        timeout_seconds=5, max_concurrency=10, rate_limit_per_minute=1
    )

    _patch_request(monkeypatch, _FakeRequest(client_host="203.0.113.5"))
    assert await limits.on_call_tool(cast(MiddlewareContext, None), _noop_call) == "ok"
    with pytest.raises(ToolError, match="limite de chamadas"):
        await limits.on_call_tool(cast(MiddlewareContext, None), _noop_call)

    # A different client has its own, unexhausted budget.
    _patch_request(monkeypatch, _FakeRequest(client_host="198.51.100.9"))
    assert await limits.on_call_tool(cast(MiddlewareContext, None), _noop_call) == "ok"


async def test_rate_limit_window_resets_after_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_request(monkeypatch, _FakeRequest(client_host="203.0.113.5"))
    limits = OperationalLimitsMiddleware(
        timeout_seconds=5,
        max_concurrency=10,
        rate_limit_per_minute=1,
        rate_limit_window_seconds=1000.0,
    )

    fake_now = [1_000.0]
    monkeypatch.setattr("causaganha_mcp.http_server.time.monotonic", lambda: fake_now[0])

    assert await limits.on_call_tool(cast(MiddlewareContext, None), _noop_call) == "ok"
    with pytest.raises(ToolError, match="limite de chamadas"):
        await limits.on_call_tool(cast(MiddlewareContext, None), _noop_call)

    fake_now[0] += 1000.0  # past the window
    assert await limits.on_call_tool(cast(MiddlewareContext, None), _noop_call) == "ok"


async def test_rate_limit_uses_x_forwarded_for_first_hop(monkeypatch: pytest.MonkeyPatch) -> None:
    limits = OperationalLimitsMiddleware(
        timeout_seconds=5, max_concurrency=10, rate_limit_per_minute=1
    )

    # Same declared client.host but different X-Forwarded-For first hops:
    # the forwarded IP is the real caller identity behind a proxy, so each
    # gets its own budget.
    _patch_request(
        monkeypatch,
        _FakeRequest(
            client_host="10.0.0.1",
            headers={"X-Forwarded-For": "203.0.113.5, 10.0.0.1"},
        ),
    )
    assert await limits.on_call_tool(cast(MiddlewareContext, None), _noop_call) == "ok"
    with pytest.raises(ToolError, match="limite de chamadas"):
        await limits.on_call_tool(cast(MiddlewareContext, None), _noop_call)

    _patch_request(
        monkeypatch,
        _FakeRequest(
            client_host="10.0.0.1",
            headers={"X-Forwarded-For": "198.51.100.9, 10.0.0.1"},
        ),
    )
    assert await limits.on_call_tool(cast(MiddlewareContext, None), _noop_call) == "ok"


async def test_rate_limit_disabled_when_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_request(monkeypatch, _FakeRequest(client_host="203.0.113.5"))
    limits = OperationalLimitsMiddleware(
        timeout_seconds=5, max_concurrency=10, rate_limit_per_minute=None
    )

    for _ in range(5):
        assert await limits.on_call_tool(cast(MiddlewareContext, None), _noop_call) == "ok"


async def test_rate_limit_falls_back_when_no_http_request(monkeypatch: pytest.MonkeyPatch) -> None:
    # Outside a real HTTP request (e.g. the pre-existing tests that call
    # on_call_tool directly with context=None), get_http_request() raises --
    # the limiter must not propagate that as an unhandled error.
    _patch_request(monkeypatch, None)
    limits = OperationalLimitsMiddleware(
        timeout_seconds=5, max_concurrency=10, rate_limit_per_minute=2
    )

    assert await limits.on_call_tool(cast(MiddlewareContext, None), _noop_call) == "ok"
    assert await limits.on_call_tool(cast(MiddlewareContext, None), _noop_call) == "ok"
    with pytest.raises(ToolError, match="limite de chamadas"):
        await limits.on_call_tool(cast(MiddlewareContext, None), _noop_call)
