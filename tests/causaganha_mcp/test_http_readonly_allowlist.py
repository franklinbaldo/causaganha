"""HTTP security boundary is the explicit public MCP profile, not a runtime blacklist."""

from __future__ import annotations

import causaganha_mcp.http_server as http_entry
from causaganha_mcp.profiles import OPERATOR_ONLY_TOOL_NAMES, PUBLIC_TOOL_NAMES


async def test_http_catalog_is_exactly_the_declared_public_profile() -> None:
    names = {tool.name for tool in await http_entry.mcp.list_tools()}

    assert names == PUBLIC_TOOL_NAMES


async def test_http_catalog_never_registers_operator_only_tools() -> None:
    names = {tool.name for tool in await http_entry.mcp.list_tools()}

    assert names.isdisjoint(OPERATOR_ONLY_TOOL_NAMES)
