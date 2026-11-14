"""Contract between the README's public MCP job list and the canonical MCP catalog."""

from __future__ import annotations

import re
from pathlib import Path

from causaganha.decisoes.published import unpublished_fontes
from causaganha_mcp.profiles import build_public_server


_ROOT = Path(__file__).parents[2]
_README = _ROOT / "README.md"

_EXPECTED_PUBLIC_JOBS = {
    "processo_consultar": "ARQUIVO",
    "publicacoes_buscar": "ARQUIVO",
    "processo_estado": "ESTADO",
    "decisoes_buscar": "TEOR",
}

# "todas" is the aggregate default, not a distinct source.
_AGGREGATE_FONTE = "todas"

_PRODUCT_BLOCK_RE = re.compile(r"Tools de produto.*?\n\n(?P<block>.*?)\n\n", re.DOTALL)
_PRODUCT_JOB_RE = re.compile(r"^- `(?P<tool>\w+)` — (?P<role>ARQUIVO|ESTADO|TEOR):", re.MULTILINE)


def _readme_public_jobs() -> dict[str, str]:
    """Read the product-job list (tool -> role) from the README's mcp-tools block."""
    source = _README.read_text(encoding="utf-8")
    start = source.index("<!-- mcp-tools:start -->")
    end = source.index("<!-- mcp-tools:end -->")
    match = _PRODUCT_BLOCK_RE.search(source[start:end])
    assert match is not None, "README.md precisa listar as tools de produto"
    return {
        job.group("tool"): job.group("role")
        for job in _PRODUCT_JOB_RE.finditer(match.group("block"))
    }


async def _decisoes_buscar_fonte_enum() -> set[str]:
    tools = await build_public_server().list_tools()
    (decisoes_buscar,) = (tool for tool in tools if tool.name == "decisoes_buscar")
    enum_values = set(decisoes_buscar.parameters["properties"]["fonte"]["enum"])
    return enum_values - {_AGGREGATE_FONTE}


def test_readme_freezes_the_public_job_set() -> None:
    """Keep the public ARQUIVO/ESTADO/TEOR surface intentionally small."""
    assert _readme_public_jobs() == _EXPECTED_PUBLIC_JOBS


async def test_readme_only_names_registered_mcp_tools() -> None:
    """A rename/removal in the public profile must not silently stale the documentation."""
    catalog = {tool.name for tool in await build_public_server().list_tools()}
    assert set(_readme_public_jobs()) <= catalog


async def test_unpublished_fontes_are_recognized_by_decisoes_buscar() -> None:
    """The publication authority may only mark fontes that decisoes_buscar recognizes (#1036)."""
    assert unpublished_fontes() <= await _decisoes_buscar_fonte_enum()
