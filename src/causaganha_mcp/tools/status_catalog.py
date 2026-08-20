"""Register ``causaganha_status`` from the typed OKF Pipeline catalog.

Pipeline-specific facts remain in :mod:`causaganha_mcp.tools.status`; this
module owns only the product-level catalog/dispatch decision. The OKF relation
is the source of stable pipeline identity and package metadata, while direct
Python service calls remain the execution boundary (never recursive MCP).
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from causaganha_mcp import knowledge
from causaganha_mcp.tools import status

if TYPE_CHECKING:
    from fastmcp import FastMCP


def _pipeline_statuses(
    metadata: tuple[knowledge.PipelineMetadata, ...] | None = None,
) -> list[status.PipelineStatus]:
    """Resolve declared pipeline metadata to direct service-layer loaders."""
    declared = metadata if metadata is not None else knowledge.load_pipeline_metadata()
    by_tool = {item.mcp_status: item for item in declared}
    if len(by_tool) != len(declared):
        message = "knowledge Pipeline relation contains duplicate mcp_status values"
        raise RuntimeError(message)

    bindings = status.pipeline_status_loaders()
    expected_tools = {tool for tool, _loader in bindings}
    declared_tools = set(by_tool)
    if declared_tools != expected_tools:
        missing = sorted(expected_tools - declared_tools)
        unknown = sorted(declared_tools - expected_tools)
        message = (
            f"knowledge Pipeline bindings disagree with code: missing={missing}, unknown={unknown}"
        )
        raise RuntimeError(message)

    results: list[status.PipelineStatus] = []
    for tool_name, loader in bindings:
        item = by_tool[tool_name]
        try:
            import_module(f"{item.pacote}.service")
        except ImportError as error:
            message = f"Pipeline {item.nome!r} declares unavailable package {item.pacote!r}"
            raise RuntimeError(message) from error

        result = loader()
        if result.nome != item.nome:
            message = f"Pipeline {item.nome!r} is bound to loader returning {result.nome!r}"
            raise RuntimeError(message)
        results.append(result)
    return results


def register(mcp: FastMCP) -> None:
    """Register the aggregate status tool using the typed OKF catalog."""

    @mcp.tool(
        name="causaganha_status",
        annotations={
            "title": "Panorama agregado dos pipelines do CausaGanha",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def causaganha_status() -> status.CausaganhaStatusResult:
        """Panorama dos pipelines declarados no catálogo OKF do CausaGanha.

        Identidade, pacote, fonte e tool de status vêm da relação tipada
        ``knowledge/Pipeline``. A execução continua chamando diretamente as
        camadas ``service.py`` de cada pacote; nenhuma tool MCP chama outra tool
        via protocolo. Falha em um manifest individual continua produzindo
        resultado parcial, mas falha/divergência do catálogo de metadados é
        explícita para não retornar silenciosamente um panorama obsoleto.
        """
        return status.CausaganhaStatusResult(pipelines=_pipeline_statuses())
