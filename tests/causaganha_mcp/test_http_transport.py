"""HTTP transport must expose the same semantic MCP facade as local stdio."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, cast

import pytest
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import MiddlewareContext

import causaganha_mcp.__main__ as stdio_entry
import causaganha_mcp.http_server as http_entry
from causaganha_mcp.http_server import (
    HttpSettings,
    OperationalLimitsMiddleware,
    PathArgumentGuardMiddleware,
)
from causaganha_mcp.server import build_server


if TYPE_CHECKING:
    from fastmcp import FastMCP


async def _catalog_signature(
    server: FastMCP,
) -> dict[str, tuple[dict[str, Any], dict[str, Any] | None]]:
    tools = await server.list_tools()
    return {
        tool.name: (
            tool.parameters,
            tool.output_schema,
        )
        for tool in tools
    }


def test_http_settings_are_loopback_safe_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "CAUSAGANHA_MCP_HOST",
        "CAUSAGANHA_MCP_PORT",
        "CAUSAGANHA_MCP_PATH",
        "CAUSAGANHA_MCP_TOOL_TIMEOUT_SECONDS",
        "CAUSAGANHA_MCP_MAX_CONCURRENCY",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = HttpSettings.from_env()

    assert settings == HttpSettings(
        host="127.0.0.1",
        port=8000,
        path="/mcp",
        tool_timeout_seconds=45.0,
        max_concurrency=4,
    )


def test_http_settings_support_explicit_deployment_bind_and_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CAUSAGANHA_MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("CAUSAGANHA_MCP_PORT", "8080")
    monkeypatch.setenv("CAUSAGANHA_MCP_PATH", "/api/mcp")
    monkeypatch.setenv("CAUSAGANHA_MCP_TOOL_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("CAUSAGANHA_MCP_MAX_CONCURRENCY", "2")

    assert HttpSettings.from_env() == HttpSettings(
        host="0.0.0.0",
        port=8080,
        path="/api/mcp",
        tool_timeout_seconds=30.0,
        max_concurrency=2,
    )


@pytest.mark.parametrize("value", ["zero", "0", "65536"])
def test_http_settings_reject_invalid_port(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("CAUSAGANHA_MCP_PORT", value)

    with pytest.raises(ValueError, match="CAUSAGANHA_MCP_PORT"):
        HttpSettings.from_env()


def test_http_settings_reject_path_without_leading_slash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CAUSAGANHA_MCP_PATH", "mcp")

    with pytest.raises(ValueError, match="CAUSAGANHA_MCP_PATH"):
        HttpSettings.from_env()


@pytest.mark.parametrize("value", ["zero", "0", "-1"])
def test_http_settings_reject_invalid_timeout(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("CAUSAGANHA_MCP_TOOL_TIMEOUT_SECONDS", value)

    with pytest.raises(ValueError, match="CAUSAGANHA_MCP_TOOL_TIMEOUT_SECONDS"):
        HttpSettings.from_env()


@pytest.mark.parametrize("value", ["1.5", "0", "-1"])
def test_http_settings_reject_invalid_concurrency(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("CAUSAGANHA_MCP_MAX_CONCURRENCY", value)

    with pytest.raises(ValueError, match="CAUSAGANHA_MCP_MAX_CONCURRENCY"):
        HttpSettings.from_env()


def test_http_entrypoint_uses_streamable_http_stateless_with_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    middleware: list[object] = []

    class FakeTool:
        def __init__(self, name: str) -> None:
            self.name = name

    class FakeServer:
        def add_middleware(self, item: object) -> None:
            middleware.append(item)

        async def list_tools(self) -> list[FakeTool]:
            return [FakeTool(name) for name in http_entry._READ_ONLY_TOOL_NAMES]

        def run(self, **kwargs: object) -> None:
            calls.append(kwargs)

    monkeypatch.setattr(http_entry, "mcp", FakeServer())
    monkeypatch.setenv("CAUSAGANHA_MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("CAUSAGANHA_MCP_PORT", "8080")
    monkeypatch.setenv("CAUSAGANHA_MCP_PATH", "/mcp")
    monkeypatch.setenv("CAUSAGANHA_MCP_TOOL_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("CAUSAGANHA_MCP_MAX_CONCURRENCY", "2")

    http_entry.main()

    assert len(middleware) == 2
    guard, limits = middleware
    assert isinstance(guard, PathArgumentGuardMiddleware)
    assert isinstance(limits, OperationalLimitsMiddleware)
    assert limits.timeout_seconds == 30.0
    assert limits.max_concurrency == 2
    assert calls == [
        {
            "transport": "http",
            "host": "0.0.0.0",
            "port": 8080,
            "path": "/mcp",
            "stateless_http": True,
        }
    ]


async def test_operational_limits_classify_timeout_as_failure() -> None:
    limits = OperationalLimitsMiddleware(timeout_seconds=0.01, max_concurrency=1)

    async def slow_call(_context: MiddlewareContext) -> str:
        await asyncio.sleep(0.05)
        return "unexpected"

    with pytest.raises(ToolError, match="Timeout não significa ausência de dado"):
        await limits.on_call_tool(cast(MiddlewareContext, None), slow_call)


async def test_operational_limits_reject_saturation_without_waiting() -> None:
    limits = OperationalLimitsMiddleware(timeout_seconds=1, max_concurrency=1)
    entered = asyncio.Event()
    release = asyncio.Event()

    async def held_call(_context: MiddlewareContext) -> str:
        entered.set()
        await release.wait()
        return "ok"

    first = asyncio.create_task(limits.on_call_tool(cast(MiddlewareContext, None), held_call))
    await entered.wait()

    with pytest.raises(ToolError, match="temporariamente saturado"):
        await limits.on_call_tool(cast(MiddlewareContext, None), held_call)

    release.set()
    assert await first == "ok"


def test_stdio_and_http_entrypoints_start_from_same_server_instance() -> None:
    assert stdio_entry.mcp is http_entry.mcp


async def test_http_catalog_matches_fresh_canonical_server() -> None:
    expected = await _catalog_signature(build_server())
    actual = await _catalog_signature(http_entry.mcp)

    assert actual == expected
