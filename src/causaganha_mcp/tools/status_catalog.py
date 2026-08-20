"""Register ``causaganha_status`` from the typed OKF Pipeline catalog.

Pipeline-specific facts remain in :mod:`causaganha_mcp.tools.status`; this
module owns only the product-level catalog/dispatch decision. The OKF relation
is the source of stable pipeline identity and package metadata, while direct
Python service calls remain the execution boundary (never recursive MCP).
"""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType
from typing import TYPE_CHECKING

import datajud.service as datajud_service
import djen_backup.service as djen_backup_service
import stj_acordaos.service as stj_acordaos_service
import tjro_juris.service as tjro_juris_service

from causaganha_mcp.knowledge import PipelineMetadata, load_pipeline_metadata
from causaganha_mcp.tools.status import (
    CausaganhaStatusResult,
    PipelineStatus,
    _datajud_status,
    _djen_status,
    _stj_acordaos_status,
    _tjro_juris_status,
)

if TYPE_CHECKING:
    from fastmcp import FastMCP


_StatusLoader = Callable[[], PipelineStatus]
_Binding = tuple[str, ModuleType, _StatusLoader]

# Keys are executable MCP surface names, not a second product catalog. The
# Pipeline relation supplies pipeline identity/package/source; these bindings
# say only which direct Python service implementation backs each declared tool.
_BINDINGS: tuple[_Binding, ...] = (
    ("djen_backup_status", djen_backup_service, _djen_status),
    ("tjro_juris_status", tjro_juris_service, _tjro_juris_status),
    ("stj_acordaos_status", stj_acordaos_service, _stj_acordaos_status),
    ("datajud_status", datajud_service, _datajud_status),
)


def _pipeline_statuses(
    metadata: tuple[PipelineMetadata, ...] | None = None,
) -> list[PipelineStatus]:
    """Resolve declared pipeline metadata to direct service-layer loaders."""
    declared = metadata if metadata is not None else load_pipeline_metadata()
    by_tool = {item.mcp_status: item for item in declared}
    if len(by_tool) != len(declared):
        message = "knowledge Pipeline relation contains duplicate mcp_status values"
        raise RuntimeError(message)

    expected_tools = {tool for tool, _service, _loader in _BINDINGS}
    declared_tools = set(by_tool)
    if declared_tools != expected_tools:
        missing = sorted(expected_tools - declared_tools)
        unknown = sorted(declared_tools - expected_tools)
        message = (
            f"knowledge Pipeline bindings disagree with code: missing={missing}, unknown={unknown}"
        )
        raise RuntimeError(message)

    results: list[PipelineStatus] = []
    for tool_name, service_module, loader in _BINDINGS:
        item = by_tool[tool_name]
        package = service_module.__name__.split(".", maxsplit=1)[0]
        if item.pacote != package:
            message = (
                f"Pipeline {item.nome!r} declares package {item.pacote!r}; code uses {package!r}"
            )
            raise RuntimeError(message)
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
    def causaganha_status() -> CausaganhaStatusResult:
        """Panorama dos pipelines declarados no catálogo OKF do CausaGanha.

        Identidade, pacote, fonte e tool de status vêm da relação tipada
        ``knowledge/Pipeline``. A execução continua chamando diretamente as
        camadas ``service.py`` de cada pacote; nenhuma tool MCP chama outra tool
        via protocolo. Falha em um manifest individual continua produzindo
        resultado parcial, mas falha/divergência do catálogo de metadados é
        explícita para não retornar silenciosamente um panorama obsoleto.
        """
        return CausaganhaStatusResult(pipelines=_pipeline_statuses())
