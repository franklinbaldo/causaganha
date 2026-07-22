"""Schema-level guarantees for causaganha_mcp tools (RFC 0013 Fase 3A/3B, RFC 0014 M1).

Fase 3A's explicit acceptance bar: every tool is read-only (`readOnlyHint`),
and no credential ever appears in a tool's input or output schema — not
"empty", not "optional", genuinely absent as a field. Same bar Fase 2.5's
`cli_contract` gate set for the CLIs themselves (see
`tests/cli_contract/test_semantic_argv_contract.py`). Fase 3B's
`datajud_facetas` is read-only too (it aggregates, never mutates) even
though — unlike the Fase 3A tools — it makes a real network call
(`openWorldHint=True`), so it stays in the same read-only/no-credential bar.

RFC 0014 M1 adds `causaganha_status` and renames every tool's output *and
input* fields to Portuguese (`encontrado`, `ultima_atualizacao`, `fonte`,
`canonica`, `aviso`, `diretorio_dados`, `caminho_manifesto`,
`arquivo_manifesto`, ...) — a deliberate schema change made before any real
consumer exists (RFC 0014 §2), locked here with an exact-property-set test
per tool (both `parameters` and `output_schema`) so a future edit can't
silently drop or rename an envelope field, or leave an English identifier
in the input schema while only the output gets translated.
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
    "causaganha_status",
]

_CREDENTIAL_SUBSTRINGS = ("key", "secret", "token", "credential", "password")

# Locks the RFC 0014 M1 envelope: every local status tool exposes exactly
# this field set, no more, no less. `causaganha_status` and `datajud_facetas`
# have their own shapes (aggregate/live-query), asserted separately below.
_ENVELOPE_FIELDS = {"encontrado", "total", "ultima_atualizacao", "fonte", "canonica", "aviso"}

_EXPECTED_OUTPUT_FIELDS = {
    "datajud_status": _ENVELOPE_FIELDS | {"ok", "com_docs", "sem_docs", "com_erro"},
    "tjro_juris_status": _ENVELOPE_FIELDS | {"enviados", "pendentes"},
    "stj_acordaos_status": _ENVELOPE_FIELDS | {"enviados", "pendentes"},
    "djen_backup_status": _ENVELOPE_FIELDS
    | {"enviados", "disponiveis", "ausentes", "desconhecidos"},
    "datajud_facetas": {"tribunal", "por", "total", "grupos", "consultado_em"},
    "causaganha_status": {"pipelines"},
}

# Input parameter names are product text too (RFC 0014 review) — an English
# `data_dir` sitting in `parameters.properties` while the output is all
# Portuguese would be exactly the half-translated schema the review flagged.
_EXPECTED_INPUT_FIELDS = {
    "datajud_status": {"diretorio_dados"},
    "tjro_juris_status": {"diretorio_dados"},
    "stj_acordaos_status": {"caminho_manifesto"},
    "djen_backup_status": {"arquivo_manifesto"},
    "datajud_facetas": {"tribunal", "por", "limite"},
    "causaganha_status": set(),
}


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


@pytest.mark.parametrize("name", TOOL_NAMES)
async def test_tool_output_schema_has_exactly_the_expected_fields(mcp, name) -> None:
    tool = await mcp.get_tool(name)
    assert tool is not None
    assert _property_names(tool.output_schema) == _EXPECTED_OUTPUT_FIELDS[name]


@pytest.mark.parametrize("name", TOOL_NAMES)
async def test_tool_input_schema_has_exactly_the_expected_fields(mcp, name) -> None:
    tool = await mcp.get_tool(name)
    assert tool is not None
    assert _property_names(tool.parameters) == _EXPECTED_INPUT_FIELDS[name]


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
