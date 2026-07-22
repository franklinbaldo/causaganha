"""Schema-level guarantees for causaganha_mcp tools (RFC 0013 Fase 3A).

Fase 3A's explicit acceptance bar: every tool is read-only (`readOnlyHint`),
and no credential ever appears in a tool's input or output schema — not
"empty", not "optional", genuinely absent as a field. Same bar Fase 2.5's
`cli_contract` gate set for the CLIs themselves (see
`tests/cli_contract/test_semantic_argv_contract.py`).
"""

from __future__ import annotations

import pytest

from causaganha_mcp.server import build_server


TOOL_NAMES = [
    "datajud_status",
    "tjro_juris_status",
    "stj_acordaos_status",
    "djen_backup_status",
]

_CREDENTIAL_SUBSTRINGS = ("key", "secret", "token", "credential", "password")


def _property_names(schema: dict | None) -> set[str]:
    if not schema:
        return set()
    return set(schema.get("properties", {}).keys())


@pytest.fixture
def mcp():
    return build_server()


@pytest.mark.parametrize("name", TOOL_NAMES)
async def test_tool_is_read_only(mcp, name) -> None:
    tool = await mcp.get_tool(name)
    assert tool is not None
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.destructiveHint is False


@pytest.mark.parametrize("name", TOOL_NAMES)
async def test_tool_has_no_credential_fields(mcp, name) -> None:
    tool = await mcp.get_tool(name)
    assert tool is not None
    field_names = _property_names(tool.parameters) | _property_names(tool.output_schema)
    for field_name in field_names:
        lowered = field_name.lower()
        for bad in _CREDENTIAL_SUBSTRINGS:
            assert bad not in lowered, f"{name}: field {field_name!r} looks credential-like"


@pytest.mark.parametrize("name", TOOL_NAMES)
async def test_tool_has_a_description(mcp, name) -> None:
    """Tools are selected by their description (mcp-coding skill) — never blank."""
    tool = await mcp.get_tool(name)
    assert tool is not None
    assert tool.description
    assert len(tool.description) > 20  # sanity floor, not a real constraint


async def test_server_exposes_exactly_the_fase_3a_tools(mcp) -> None:
    """No ingestion/upload tool exists yet — Fase 3A is read-only status only."""
    tools = await mcp.list_tools()
    assert {t.name for t in tools} == set(TOOL_NAMES)
