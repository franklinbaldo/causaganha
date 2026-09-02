"""Contract between the README's public MCP catalog and ``build_server()``.

The README documents the MCP surface for humans and agents that read the
repository before touching code. A tool renamed, added or removed in
``build_server()`` without a matching README update silently misleads that
reader — this guards against exactly that drift (issue #992).
"""

from __future__ import annotations

import re
from pathlib import Path

from causaganha_mcp.server import build_server


_README = Path(__file__).parents[2] / "README.md"

_START_MARKER = "<!-- mcp-tools:start -->"
_END_MARKER = "<!-- mcp-tools:end -->"

_PRODUCT_JOB_BY_TOOL = {
    "processo_consultar": "ARQUIVO",
    "publicacoes_buscar": "ARQUIVO",
    "processo_estado": "ESTADO",
    "decisoes_buscar": "TEOR",
}


def _catalog_section() -> str:
    text = _README.read_text(encoding="utf-8")
    start = text.index(_START_MARKER) + len(_START_MARKER)
    end = text.index(_END_MARKER, start)
    return text[start:end]


def _documented_tool_names() -> set[str]:
    return set(re.findall(r"`([a-z][a-z0-9_]*)`", _catalog_section()))


async def _canonical_tool_names() -> set[str]:
    return {tool.name for tool in await build_server().list_tools()}


async def test_readme_documents_exactly_the_tools_build_server_exposes() -> None:
    """A rename/removal in build_server() must not silently stale the README."""
    assert _documented_tool_names() == await _canonical_tool_names()


def test_readme_no_longer_hardcodes_a_stale_tool_count() -> None:
    text = _README.read_text(encoding="utf-8")
    assert "sete tools" not in text


def test_readme_lists_every_product_job_tool_in_the_catalog_section() -> None:
    section = _catalog_section()
    for tool_name in _PRODUCT_JOB_BY_TOOL:
        assert f"`{tool_name}`" in section


def test_readme_distinguishes_product_tools_from_operational_status_tools() -> None:
    section = _catalog_section()
    assert "produto" in section.lower()
    assert "operacion" in section.lower() or "diagnóstico" in section.lower()


def test_readme_http_state_describes_stdio_artifact_and_public_url_separately() -> None:
    text = _README.read_text(encoding="utf-8")
    idx = text.index("### 3. Agentes / MCP")
    http_section = text[idx : idx + 2000]

    assert "stdio" in http_section.lower()
    assert "deployment/mcp" in http_section
    assert "#950" in http_section
    assert not re.search(r"não est[áa] configurado neste reposit[óo]rio", http_section)


def test_readme_publishes_no_fictional_remote_mcp_url() -> None:
    text = _README.read_text(encoding="utf-8")
    assert "https://causaganha" not in text
