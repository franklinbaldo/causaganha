"""Schema-level guarantees for causaganha_mcp tools.

Every MCP tool is read-only and credential-free at the protocol boundary.
Product-facing tools use Portuguese field names and explicit schemas so an
agent can select and interpret them without learning repository internals.
"""

from __future__ import annotations

import pytest

from causaganha_mcp.server import build_server
from datajud.client import FACET_FIELDS


TOOL_NAMES = [
    "datajud_status",
    "datajud_facetas",
    "processo_estado",
    "tjro_juris_status",
    "stj_acordaos_status",
    "djen_backup_status",
    "causaganha_status",
    "processo_consultar",
]

_CREDENTIAL_SUBSTRINGS = ("key", "secret", "token", "credential", "password")

_ENVELOPE_FIELDS = {"encontrado", "total", "ultima_atualizacao", "fonte", "canonica", "aviso"}

_EXPECTED_OUTPUT_FIELDS = {
    "datajud_status": _ENVELOPE_FIELDS | {"ok", "com_docs", "sem_docs", "com_erro"},
    "tjro_juris_status": _ENVELOPE_FIELDS | {"enviados", "pendentes"},
    "stj_acordaos_status": _ENVELOPE_FIELDS | {"enviados", "pendentes"},
    "djen_backup_status": _ENVELOPE_FIELDS
    | {"enviados", "disponiveis", "ausentes", "desconhecidos"},
    "datajud_facetas": {"tribunal", "por", "total", "grupos", "consultado_em"},
    "processo_estado": {
        "encontrado",
        "cnj",
        "cnj_formatado",
        "tribunal",
        "natureza",
        "resumo",
        "graus",
        "total_movimentos",
        "marcos",
        "marcos_truncados",
        "ultimo_marco",
        "movimentos",
        "movimentos_truncados",
        "consultado_em",
        "fonte_oficial",
        "limitacoes",
        "next_actions",
    },
    "causaganha_status": {"pipelines"},
    "processo_consultar": {
        "encontrado",
        "cnj",
        "cnj_formatado",
        "fontes_presentes",
        "cobertura_dataset",
        "djen",
        "juris",
        "stj",
        "datajud",
        "documentos",
        "documentos_truncados",
        "dataset_gerado_em",
        "consultado_em",
        "fonte",
        "canonica",
        "avisos",
        "web_url",
        "web_path",
    },
}

_EXPECTED_INPUT_FIELDS = {
    "datajud_status": {"diretorio_dados"},
    "tjro_juris_status": {"diretorio_dados"},
    "stj_acordaos_status": {"caminho_manifesto"},
    "djen_backup_status": {"arquivo_manifesto"},
    "datajud_facetas": {"tribunal", "por", "limite"},
    "processo_estado": {
        "cnj",
        "tribunal",
        "incluir_movimentos",
        "limite_marcos",
        "limite_movimentos",
    },
    "causaganha_status": set(),
    "processo_consultar": {"cnj", "incluir_documentos", "limite_documentos"},
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
    """Tools are selected by their description — never leave it blank."""
    tool = await mcp.get_tool(name)
    assert tool is not None
    assert tool.description
    assert len(tool.description) > 20


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
    """Guard the hardcoded MCP enum against the DataJud client map drifting."""
    tool = await mcp.get_tool("datajud_facetas")
    assert tool is not None
    por_schema = tool.parameters["properties"]["por"]
    assert set(por_schema["enum"]) == set(FACET_FIELDS.keys())
