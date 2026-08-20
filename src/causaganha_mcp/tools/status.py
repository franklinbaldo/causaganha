"""``causaganha_status`` — panorama agregado dos quatro pipelines (RFC 0014 M1).

Os fatos de cada pipeline continuam vindo diretamente de seus ``service.py``.
A identidade estável do produto — nome, pacote, fonte e tool de status — vem
agora da relação tipada ``Pipeline`` em ``knowledge/``. Não há chamada MCP
recursiva e nenhum contrato físico de dados foi movido para Markdown.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

import datajud.service as datajud_service
import djen_backup.service as djen_backup_service
import stj_acordaos.service as stj_acordaos_service
import tjro_juris.service as tjro_juris_service
from causaganha_mcp import knowledge

from datajud.manifest import ManifestFormatError as DatajudManifestFormatError
from tjro_juris.manifest import ManifestFormatError as TjroJurisManifestFormatError

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastmcp import FastMCP


_TJRO_JURIS_DEFAULT_DATA_DIR = "data/tjro-juris"

_DJEN_CANONICAL_NOTE = (
    "Origem local, não canônica: a fonte de verdade do DJEN é o "
    "sync-manifest.parquet no Internet Archive — este manifest local pode "
    "estar atrasado em relação a ele."
)


class PipelineStatus(BaseModel):
    """Panorama de um único pipeline dentro do resultado agregado."""

    nome: Literal["djen", "tjro_juris", "stj_acordaos", "datajud"] = Field(
        description="Identificador do pipeline."
    )
    encontrado: bool = Field(
        description="False quando não há manifest ou dado algum nesta máquina para este pipeline."
    )
    total: int = Field(description="Total de itens registrados (unidade específica do pipeline).")
    contagens: dict[str, int] = Field(
        description="Contagens específicas deste pipeline, com os mesmos nomes de campo "
        "que a tool `<pipeline>_status` correspondente retorna."
    )
    ultima_atualizacao: str | None = Field(
        default=None,
        description="Timestamp (ISO 8601) da entrada mais recentemente atualizada, ou "
        "None quando não há nenhuma entrada.",
    )
    fonte: Literal["manifest_local", "cache_local"] = Field(
        description="'manifest_local': o manifest é a própria fonte de verdade. "
        "'cache_local': cache que pode estar atrasado em relação a uma fonte canônica "
        "remota (ver `canonica`/`aviso`)."
    )
    canonica: bool = Field(
        description="False quando existe uma fonte remota mais autoritativa que este "
        "manifest local (ver `aviso`)."
    )
    aviso: str | None = Field(default=None, description="Ressalva relevante, quando houver.")


class CausaganhaStatusResult(BaseModel):
    """Panorama agregado dos quatro pipelines locais do CausaGanha."""

    pipelines: list[PipelineStatus] = Field(
        description="Um item por pipeline: djen, tjro_juris, stj_acordaos, datajud."
    )


def _djen_status() -> PipelineStatus:
    try:
        result = djen_backup_service.manifest_status(djen_backup_service.DEFAULT_MANIFEST_FILE)
    except OSError as exc:
        return PipelineStatus(
            nome="djen",
            encontrado=False,
            total=0,
            contagens={},
            fonte="cache_local",
            canonica=False,
            aviso=f"Não foi possível ler o manifest local: {exc}",
        )
    return PipelineStatus(
        nome="djen",
        encontrado=result.total > 0,
        total=result.total,
        contagens={
            "enviados": result.uploaded,
            "disponiveis": result.available,
            "ausentes": result.absent,
            "desconhecidos": result.unknown,
        },
        ultima_atualizacao=result.ultima_atualizacao or None,
        fonte="cache_local",
        canonica=False,
        aviso=_DJEN_CANONICAL_NOTE,
    )


def _tjro_juris_status() -> PipelineStatus:
    try:
        result = tjro_juris_service.manifest_status(Path(_TJRO_JURIS_DEFAULT_DATA_DIR))
    except (OSError, TjroJurisManifestFormatError) as exc:
        return PipelineStatus(
            nome="tjro_juris",
            encontrado=False,
            total=0,
            contagens={},
            fonte="manifest_local",
            canonica=True,
            aviso=f"Não foi possível ler o manifest local: {exc}",
        )
    return PipelineStatus(
        nome="tjro_juris",
        encontrado=result.total > 0,
        total=result.total,
        contagens={"enviados": result.uploaded, "pendentes": result.pending},
        ultima_atualizacao=result.ultima_atualizacao or None,
        fonte="manifest_local",
        canonica=True,
    )


def _stj_acordaos_status() -> PipelineStatus:
    try:
        result = stj_acordaos_service.manifest_summary(stj_acordaos_service.DEFAULT_MANIFEST)
    except OSError as exc:
        return PipelineStatus(
            nome="stj_acordaos",
            encontrado=False,
            total=0,
            contagens={},
            fonte="manifest_local",
            canonica=True,
            aviso=f"Não foi possível ler o manifest local: {exc}",
        )
    return PipelineStatus(
        nome="stj_acordaos",
        encontrado=result.count > 0,
        total=result.count,
        contagens={"enviados": result.uploaded, "pendentes": result.pending},
        ultima_atualizacao=result.ultima_atualizacao or None,
        fonte="manifest_local",
        canonica=True,
    )


def _datajud_status() -> PipelineStatus:
    try:
        result = datajud_service.manifest_status(datajud_service.DEFAULT_DATA_DIR)
    except (OSError, DatajudManifestFormatError) as exc:
        return PipelineStatus(
            nome="datajud",
            encontrado=False,
            total=0,
            contagens={},
            fonte="manifest_local",
            canonica=True,
            aviso=f"Não foi possível ler o manifest local: {exc}",
        )
    if result is None:
        return PipelineStatus(
            nome="datajud",
            encontrado=False,
            total=0,
            contagens={},
            fonte="manifest_local",
            canonica=True,
        )
    return PipelineStatus(
        nome="datajud",
        encontrado=True,
        total=result.total,
        contagens={
            "ok": result.ok,
            "com_docs": result.com_docs,
            "sem_docs": result.sem_docs,
            "com_erro": result.com_erro,
        },
        ultima_atualizacao=result.ultima_atualizacao or None,
        fonte="manifest_local",
        canonica=True,
    )


def pipeline_status_loaders() -> tuple[tuple[str, Callable[[], PipelineStatus]], ...]:
    """Return direct in-process bindings for aggregate pipeline status."""
    return (
        ("djen_backup_status", _djen_status),
        ("tjro_juris_status", _tjro_juris_status),
        ("stj_acordaos_status", _stj_acordaos_status),
        ("datajud_status", _datajud_status),
    )


def _pipeline_statuses(
    metadata: tuple[knowledge.PipelineMetadata, ...] | None = None,
) -> list[PipelineStatus]:
    """Resolve the typed OKF product catalog to established direct loaders."""
    declared = metadata if metadata is not None else knowledge.load_pipeline_metadata()
    by_tool = {item.mcp_status: item for item in declared}
    if len(by_tool) != len(declared):
        message = "knowledge Pipeline relation contains duplicate mcp_status values"
        raise RuntimeError(message)

    bindings = pipeline_status_loaders()
    expected_tools = {tool for tool, _loader in bindings}
    declared_tools = set(by_tool)
    if declared_tools != expected_tools:
        missing = sorted(expected_tools - declared_tools)
        unknown = sorted(declared_tools - expected_tools)
        message = (
            f"knowledge Pipeline bindings disagree with code: missing={missing}, unknown={unknown}"
        )
        raise RuntimeError(message)

    results: list[PipelineStatus] = []
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
    """Registra ``causaganha_status`` em *mcp*."""

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

        O catálogo ``Pipeline`` fornece identidade estável e binding de produto;
        cada loader continua chamando diretamente a camada ``service.py`` já
        estabelecida. Falha de um manifest individual continua virando resultado
        parcial, enquanto divergência do catálogo é explícita para evitar um
        panorama silenciosamente obsoleto.
        """
        return CausaganhaStatusResult(pipelines=_pipeline_statuses())
