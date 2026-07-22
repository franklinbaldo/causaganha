"""Schema-level guarantees for causaganha_mcp tools (RFC 0013 Fase 3A/3B).

Fase 3A's explicit acceptance bar: every tool is read-only (`readOnlyHint`),
and no credential ever appears in a tool's input or output schema — not
"empty", not "optional", genuinely absent as a field. Same bar Fase 2.5's
`cli_contract` gate set for the CLIs themselves (see
`tests/cli_contract/test_semantic_argv_contract.py`). Fase 3B's
`datajud_facetas` is read-only too (it aggregates, never mutates) even
though — unlike the Fase 3A tools — it makes a real network call
(`openWorldHint=True`), so it stays in the same read-only/no-credential bar.
"""

from __future__ import annotations

import pytest

from causaganha_mcp.server import build_server
from datajud.client import FACET_FIELDS


TOOL_NAMES = [
    "datajud_status",
    "datajud_facetas",
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


async def test_server_exposes_exactly_the_known_tools(mcp) -> None:
    """No ingestion/upload tool exists — every tool here is read-only."""
    tools = await mcp.list_tools()
    assert {t.name for t in tools} == set(TOOL_NAMES)


async def test_facetas_por_enum_matches_facet_fields(mcp) -> None:
    """Guard against `por`'s hardcoded Literal drifting from `FACET_FIELDS`.

    The tool declares `por` as a hardcoded `Literal[...]` (see
    `tools/datajud.py`) rather than deriving it dynamically from
    `datajud.client.FACET_FIELDS` — this test is the drift guard that keeps
    the two in sync.
    """
    tool = await mcp.get_tool("datajud_facetas")
    assert tool is not None
    por_schema = tool.parameters["properties"]["por"]
    assert set(por_schema["enum"]) == set(FACET_FIELDS.keys())
