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

import djen_backup.service as djen_backup_service
import stj_acordaos.service as stj_acordaos_service
import tjro_juris.service as tjro_juris_service
from causaganha_mcp import knowledge
from datajud import service as datajud_service
from datajud import state as datajud_state
from datajud.manifest import STATUS_OK, ManifestDataJud, ManifestFormatError as DatajudManifestFormatError
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
    """Panorama factual de um único pipeline dentro do resultado agregado."""

    nome: Literal["djen", "tjro_juris", "stj_acordaos", "datajud"] = Field(
        description="Identificador do pipeline."
    )
    observacao: Literal["present", "absent", "unavailable"] = Field(
        description=(
            "Estado factual da observação desta fonte: present quando foi lida, "
            "absent quando a fonte autoritativa não contém estado, unavailable "
            "quando a fonte existe/é esperada mas não pôde ser verificada."
        )
    )
    encontrado: bool = Field(
        description="True quando a fonte observada contém pelo menos um item registrado."
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
    publicado_em: str | None = Field(
        default=None,
        description="Timestamp de publicação da geração observada, quando a fonte o registra.",
    )
    geracao: str | None = Field(
        default=None,
        description="Identidade verificável da geração observada, quando disponível.",
    )
    fonte: Literal["manifest_local", "cache_local", "bundle_publicado"] = Field(
        description=(
            "Proveniência concreta da observação: manifest local, cache local ou "
            "bundle publicado e verificado."
        )
    )
    canonica: bool = Field(
        description="False quando existe uma fonte remota mais autoritativa que esta observação."
    )
    aviso: str | None = Field(default=None, description="Ressalva relevante, quando houver.")


class CausaganhaStatusResult(BaseModel):
    """Panorama agregado dos quatro pipelines do CausaGanha."""

    pipelines: list[PipelineStatus] = Field(
        description="Um item por pipeline: djen, tjro_juris, stj_acordaos, datajud."
    )


def _djen_status() -> PipelineStatus:
    try:
        result = djen_backup_service.manifest_status(djen_backup_service.DEFAULT_MANIFEST_FILE)
    except OSError as exc:
        return PipelineStatus(
            nome="djen",
            observacao="unavailable",
            encontrado=False,
            total=0,
            contagens={},
            fonte="cache_local",
            canonica=False,
            aviso=f"Não foi possível ler o manifest local: {exc}",
        )
    return PipelineStatus(
        nome="djen",
        observacao="present" if result.total > 0 else "absent",
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
            observacao="unavailable",
            encontrado=False,
            total=0,
            contagens={},
            fonte="manifest_local",
            canonica=True,
            aviso=f"Não foi possível ler o manifest local: {exc}",
        )
    return PipelineStatus(
        nome="tjro_juris",
        observacao="present" if result.total > 0 else "absent",
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
            observacao="unavailable",
            encontrado=False,
            total=0,
            contagens={},
            fonte="manifest_local",
            canonica=True,
            aviso=f"Não foi possível ler o manifest local: {exc}",
        )
    return PipelineStatus(
        nome="stj_acordaos",
        observacao="present" if result.count > 0 else "absent",
        encontrado=result.count > 0,
        total=result.count,
        contagens={"enviados": result.uploaded, "pendentes": result.pending},
        ultima_atualizacao=result.ultima_atualizacao or None,
        fonte="manifest_local",
        canonica=True,
    )


def _datajud_status() -> PipelineStatus:
    tribunal = datajud_service.DEFAULT_TRIBUNAL
    try:
        published = datajud_state.read_remote_state(tribunal)
    except datajud_state.RemoteStateError as exc:
        return PipelineStatus(
            nome="datajud",
            observacao="unavailable",
            encontrado=False,
            total=0,
            contagens={},
            fonte="bundle_publicado",
            canonica=True,
            aviso=(
                "Não foi possível verificar a geração DataJud publicada; "
                f"isso não significa dataset vazio: {exc}"
            ),
        )

    if published is None:
        return PipelineStatus(
            nome="datajud",
            observacao="absent",
            encontrado=False,
            total=0,
            contagens={},
            fonte="bundle_publicado",
            canonica=True,
            aviso="Nenhuma geração coerente DataJud foi publicada para este tribunal.",
        )

    try:
        manifest = ManifestDataJud.load_text(
            published.manifest_text,
            source=datajud_state.bundle_name(tribunal),
        )
    except DatajudManifestFormatError as exc:
        return PipelineStatus(
            nome="datajud",
            observacao="unavailable",
            encontrado=False,
            total=0,
            contagens={},
            publicado_em=published.published_at or None,
            geracao=published.generation,
            fonte="bundle_publicado",
            canonica=True,
            aviso=f"A geração publicada existe, mas seu manifest é inválido: {exc}",
        )

    entries = manifest.all_entries()
    ok = sum(1 for entry in entries if entry.status == STATUS_OK)
    com_docs = sum(1 for entry in entries if entry.status == STATUS_OK and entry.docs > 0)
    ultima_atualizacao = max(
        (entry.consultado_em for entry in entries if entry.consultado_em),
        default="",
    )
    warning = None
    if not published.published_at:
        warning = (
            "Esta geração antecede o timestamp de publicação no bundle; "
            "use ultima_atualizacao como sinal temporal do conteúdo."
        )
    return PipelineStatus(
        nome="datajud",
        observacao="present",
        encontrado=bool(entries),
        total=len(entries),
        contagens={
            "ok": ok,
            "com_docs": com_docs,
            "sem_docs": ok - com_docs,
            "com_erro": len(entries) - ok,
        },
        ultima_atualizacao=ultima_atualizacao or None,
        publicado_em=published.published_at or None,
        geracao=published.generation,
        fonte="bundle_publicado",
        canonica=True,
        aviso=warning,
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
            "openWorldHint": True,
        },
    )
    def causaganha_status() -> CausaganhaStatusResult:
        """Panorama dos pipelines declarados no catálogo OKF do CausaGanha.

        O catálogo ``Pipeline`` fornece identidade estável e binding de produto;
        cada loader continua chamando diretamente a camada ``service.py`` já
        estabelecida. A observação DataJud usa a mesma geração publicada que
        governa restore incremental; falha de uma fonte individual continua
        virando resultado parcial, enquanto divergência do catálogo é explícita.
        """
        return CausaganhaStatusResult(pipelines=_pipeline_statuses())
