"""HTTP transport must expose the same semantic MCP facade as local stdio."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

import causaganha_mcp.__main__ as stdio_entry
import causaganha_mcp.http_server as http_entry
from causaganha_mcp.http_server import HttpSettings
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
    ):
        monkeypatch.delenv(key, raising=False)

    settings = HttpSettings.from_env()

    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.path == "/mcp"


def test_http_settings_support_explicit_deployment_bind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CAUSAGANHA_MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("CAUSAGANHA_MCP_PORT", "8080")
    monkeypatch.setenv("CAUSAGANHA_MCP_PATH", "/api/mcp")

    assert HttpSettings.from_env() == HttpSettings(
        host="0.0.0.0",
        port=8080,
        path="/api/mcp",
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


def test_http_entrypoint_uses_streamable_http_stateless(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    class FakeServer:
        def run(self, **kwargs: object) -> None:
            calls.append(kwargs)

    monkeypatch.setattr(http_entry, "mcp", FakeServer())
    monkeypatch.setenv("CAUSAGANHA_MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("CAUSAGANHA_MCP_PORT", "8080")
    monkeypatch.setenv("CAUSAGANHA_MCP_PATH", "/mcp")

    http_entry.main()

    assert calls == [
        {
            "transport": "http",
            "host": "0.0.0.0",
            "port": 8080,
            "path": "/mcp",
            "stateless_http": True,
        }
    ]


def test_stdio_and_http_entrypoints_start_from_same_server_instance() -> None:
    assert stdio_entry.mcp is http_entry.mcp


async def test_http_catalog_matches_fresh_canonical_server() -> None:
    expected = await _catalog_signature(build_server())
    actual = await _catalog_signature(http_entry.mcp)

    assert actual == expected
