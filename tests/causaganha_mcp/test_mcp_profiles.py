"""Public/operator MCP catalog composition contract (#1244).

A remote-facing server must never even register a tool that accepts an
arbitrary local filesystem path — not just reject the argument at call
time. These tests prove the split is structural (which tools get
registered), not a runtime blacklist.
"""

from __future__ import annotations

from causaganha_mcp.profiles import (
    OPERATOR_ONLY_TOOL_NAMES,
    PUBLIC_TOOL_NAMES,
    build_operator_server,
    build_public_server,
)
from causaganha_mcp.server import build_server


# The three known local-filesystem escape hatches across the operator-only
# tools (causaganha_mcp/http_server.py's _PATH_ARGUMENT_TOOLS documents the
# same three names for its own, separate runtime guard).
_FORBIDDEN_PATH_PARAMS = frozenset({"diretorio_dados", "arquivo_manifesto", "caminho_manifesto"})


async def _tool_names(mcp) -> set[str]:
    return {tool.name for tool in await mcp.list_tools()}


async def test_public_profile_is_exactly_the_declared_product_catalog() -> None:
    assert await _tool_names(build_public_server()) == PUBLIC_TOOL_NAMES


async def test_public_profile_never_registers_a_local_path_argument() -> None:
    mcp = build_public_server()
    for tool in await mcp.list_tools():
        properties = set(tool.parameters.get("properties", {}))
        leaked = properties & _FORBIDDEN_PATH_PARAMS
        assert not leaked, f"{tool.name} exposes forbidden path argument(s): {leaked}"


async def test_datajud_status_is_operator_only() -> None:
    assert "datajud_status" in OPERATOR_ONLY_TOOL_NAMES
    assert "datajud_status" not in PUBLIC_TOOL_NAMES
    assert "datajud_status" not in await _tool_names(build_public_server())
    assert "datajud_status" in await _tool_names(build_operator_server())


async def test_operator_profile_matches_the_legacy_stdio_catalog_exactly() -> None:
    """build_server() (stdio) must not silently drift once it wraps profiles.py."""
    assert await _tool_names(build_operator_server()) == await _tool_names(build_server())
    assert (
        await _tool_names(build_operator_server()) == PUBLIC_TOOL_NAMES | OPERATOR_ONLY_TOOL_NAMES
    )
