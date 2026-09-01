"""Agent-experience contract for the product-facing MCP catalog.

These tests intentionally inspect only MCP metadata. A consumer that has never
seen the repository should be able to choose the right tool from names,
descriptions and schemas without knowing storage or pipeline topology.
"""

from __future__ import annotations

import pytest

from causaganha_mcp.server import build_server


@pytest.fixture
def mcp():
    return build_server()


async def _description(mcp, name: str) -> str:
    tool = await mcp.get_tool(name)
    assert tool is not None
    assert tool.description
    return tool.description.lower()


async def test_cnj_snapshot_and_live_state_are_distinguishable_from_catalog(mcp) -> None:
    snapshot = await _description(mcp, "processo_consultar")
    live = await _description(mcp, "processo_estado")

    assert "cnj" in snapshot
    assert "internet archive" in snapshot
    assert "datajud" in live
    assert "ao vivo" in live
    assert "estado processual" in live
    assert "teor" in live


async def test_publication_search_is_archive_first_and_points_to_process_context(mcp) -> None:
    description = await _description(mcp, "publicacoes_buscar")

    assert "publicações" in description
    assert "arquivo público" in description
    assert "processo_consultar" in description
    assert "processo_estado" in description
    assert "cobertura" in description


async def test_decision_search_is_content_first_and_not_current_process_state(mcp) -> None:
    description = await _description(mcp, "decisoes_buscar")

    assert "decisão" in description
    assert "acórdão" in description
    assert "teor" in description
    assert "data_inicio" in description
    assert "processo_estado" in description
    assert "processo_consultar" in description


async def test_status_tools_are_described_as_operational_not_product_prerequisites(mcp) -> None:
    server = mcp.instructions.lower()

    assert "tools `*_status`" in server
    assert "diagnóstico operacional" in server
    assert "não" in server and "etapa obrigatória" in server


async def test_server_teaches_archive_state_content_boundary(mcp) -> None:
    instructions = mcp.instructions.lower()

    assert "arquivo" in instructions
    assert "estado" in instructions
    assert "teor" in instructions
    assert "decisoes_buscar" in instructions
    assert "movimento" in instructions
    assert "não prova inexistência" in instructions


async def test_product_catalog_does_not_require_storage_vocabulary_for_tool_selection(mcp) -> None:
    """Storage details may be disclosed as provenance, but never define the job."""
    product_tools = {
        "processo_consultar",
        "processo_estado",
        "publicacoes_buscar",
        "decisoes_buscar",
    }
    for name in product_tools:
        tool = await mcp.get_tool(name)
        assert tool is not None
        title = tool.annotations.title.lower()
        assert "parquet" not in title
        assert "duckdb" not in title
        assert "manifest" not in title
