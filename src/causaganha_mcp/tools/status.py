"""``causaganha_status`` — panorama agregado dos quatro pipelines (RFC 0014 M1).

Os fatos de cada pipeline continuam vindo diretamente de sua autoridade já
estabelecida. A identidade estável do produto — nome, pacote, fonte e tool de
status — vem da relação tipada ``Pipeline`` em ``knowledge/``. Não há chamada
MCP recursiva e nenhum contrato físico de dados foi movido para Markdown.
"""

from __future__ import annotations

from email.utils import parsedate_to_datetime
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import httpx
from pydantic import BaseModel, Field

from causaganha_mcp import knowledge, workflow_runs
from datajud import state as datajud_state
from datajud.client import DEFAULT_TRIBUNAL
from datajud.manifest import STATUS_OK, ManifestDataJud
from datajud.manifest import ManifestFormatError as DatajudManifestFormatError
from djen_backup import published as djen_published
from stj_acordaos import archive as stj_acordaos_archive
from stj_acordaos.manifest import ManifestFormatError as StjManifestFormatError
from stj_acordaos.manifest import ManifestSTJ
from tjro_juris import archive as tjro_juris_archive
from tjro_juris.manifest import ManifestFormatError as TjroJurisManifestFormatError
from tjro_juris.manifest import ManifestJuris


if TYPE_CHECKING:
    from collections.abc import Callable

    from fastmcp import FastMCP


_ClockState = Literal["present", "absent", "unknown", "unavailable"]
_PUBLICATION_TIMEOUT_S = 5.0
_HTTP_NOT_FOUND = 404


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
    fonte: Literal["manifest_local", "manifest_publicado", "cache_local", "bundle_publicado"] = (
        Field(
            description=(
                "Proveniência concreta da observação: manifest/cache local ou estado publicado "
                "no Internet Archive."
            )
        )
    )
    canonica: bool = Field(
        description="False quando existe uma fonte remota mais autoritativa que esta observação."
    )
    execucao_observacao: _ClockState = Field(
        default="unknown",
        description="Estado factual do relógio de runs schedule/workflow_dispatch no GitHub Actions.",
    )
    ultima_tentativa: str | None = Field(
        default=None,
        description="Início da tentativa elegível mais recente observada no workflow.",
    )
    ultimo_sucesso: str | None = Field(
        default=None,
        description="Conclusão do sucesso elegível mais recente observado no workflow.",
    )
    execucao_aviso: str | None = Field(
        default=None,
        description="Ressalva da janela bounded de runs, quando necessária.",
    )
    publicacao_observacao: _ClockState = Field(
        default="unknown",
        description=(
            "Estado factual do relógio de publicação da autoridade do pipeline; não é health verdict."
        ),
    )
    ultima_publicacao: str | None = Field(
        default=None,
        description="Timestamp da publicação autoritativa mais recente que pôde ser provada.",
    )
    publicacao_aviso: str | None = Field(
        default=None,
        description="Ressalva específica do relógio de publicação, quando necessária.",
    )
    aviso: str | None = Field(default=None, description="Ressalva relevante, quando houver.")


class CausaganhaStatusResult(BaseModel):
    """Panorama agregado dos quatro pipelines do CausaGanha."""

    pipelines: list[PipelineStatus] = Field(
        description="Um item por pipeline: djen, tjro_juris, stj_acordaos, datajud."
    )


def _published_object_clock(url: str) -> tuple[_ClockState, str | None, str | None]:
    """Observe the modification clock of one already-authoritative IA object.

    This is deliberately independent from content-state timestamps. A missing or
    malformed ``Last-Modified`` header yields ``unknown``; transport failure yields
    ``unavailable``. Callers only use this after/alongside their normal authority read.
    """
    try:
        response = httpx.head(url, follow_redirects=True, timeout=_PUBLICATION_TIMEOUT_S)
        if response.status_code == _HTTP_NOT_FOUND:
            return "absent", None, "O objeto autoritativo não existe no Internet Archive."
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return "unavailable", None, f"Não foi possível verificar metadata de publicação: {exc}"

    raw = response.headers.get("Last-Modified")
    if not raw:
        return "unknown", None, "O objeto foi lido, mas não expôs Last-Modified verificável."
    try:
        timestamp = parsedate_to_datetime(raw).isoformat()
    except (TypeError, ValueError, OverflowError):
        return "unknown", None, f"Last-Modified inválido no objeto autoritativo: {raw!r}"
    return "present", timestamp, None


def _djen_status() -> PipelineStatus:
    try:
        manifest = djen_published.read_published_manifest()
    except djen_published.PublishedManifestUnavailable as exc:
        return PipelineStatus(
            nome="djen",
            observacao="unavailable",
            encontrado=False,
            total=0,
            contagens={},
            fonte="manifest_publicado",
            canonica=True,
            publicacao_observacao="unavailable",
            publicacao_aviso=(
                "A autoridade composta DJEN não pôde ser verificada; "
                "não há relógio de publicação observável."
            ),
            aviso=(
                "Não foi possível verificar o manifest DJEN publicado; "
                f"isso não significa dataset vazio: {exc}"
            ),
        )
    if manifest is None:
        return PipelineStatus(
            nome="djen",
            observacao="absent",
            encontrado=False,
            total=0,
            contagens={},
            fonte="manifest_publicado",
            canonica=True,
            publicacao_observacao="absent",
            aviso="Nenhum manifest DJEN foi publicado no Internet Archive.",
        )

    counts = manifest.counts()
    return PipelineStatus(
        nome="djen",
        observacao="present",
        encontrado=counts.total > 0,
        total=counts.total,
        contagens={
            "enviados": counts.uploaded,
            "disponiveis": counts.available,
            "ausentes": counts.absent,
            "desconhecidos": counts.unknown,
        },
        ultima_atualizacao=counts.ultima_atualizacao or None,
        fonte="manifest_publicado",
        canonica=True,
        publicacao_observacao="unknown",
        publicacao_aviso=(
            "DJEN usa autoridade composta (sync-manifest.parquet + manifest-log pendente); "
            "o strict reader ainda não expõe metadata coerente de todos os componentes."
        ),
    )


def _tjro_juris_status() -> PipelineStatus:
    try:
        text = tjro_juris_archive.read_manifest_text()
    except httpx.HTTPError as exc:
        return PipelineStatus(
            nome="tjro_juris",
            observacao="unavailable",
            encontrado=False,
            total=0,
            contagens={},
            fonte="manifest_publicado",
            canonica=True,
            publicacao_observacao="unavailable",
            publicacao_aviso="O manifest autoritativo não pôde ser verificado.",
            aviso=(
                "Não foi possível verificar o manifest TJRO JURIS publicado; "
                f"isso não significa dataset vazio: {exc}"
            ),
        )
    if text is None:
        return PipelineStatus(
            nome="tjro_juris",
            observacao="absent",
            encontrado=False,
            total=0,
            contagens={},
            fonte="manifest_publicado",
            canonica=True,
            publicacao_observacao="absent",
            aviso="Nenhum manifest TJRO JURIS foi publicado no Internet Archive.",
        )
    try:
        manifest = ManifestJuris.load_text(
            text,
            source=tjro_juris_archive.MANIFEST_DOWNLOAD_URL,
        )
    except TjroJurisManifestFormatError as exc:
        clock_state, last_publication, clock_warning = _published_object_clock(
            tjro_juris_archive.MANIFEST_DOWNLOAD_URL
        )
        return PipelineStatus(
            nome="tjro_juris",
            observacao="unavailable",
            encontrado=False,
            total=0,
            contagens={},
            fonte="manifest_publicado",
            canonica=True,
            publicacao_observacao=clock_state,
            ultima_publicacao=last_publication,
            publicacao_aviso=clock_warning,
            aviso=f"O manifest TJRO JURIS publicado existe, mas é inválido: {exc}",
        )
    entries = manifest.all_entries()
    uploaded = sum(1 for entry in entries if entry.ia_status == "uploaded")
    ultima_atualizacao = max(
        (entry.updated_at for entry in entries if entry.updated_at),
        default="",
    )
    clock_state, last_publication, clock_warning = _published_object_clock(
        tjro_juris_archive.MANIFEST_DOWNLOAD_URL
    )
    return PipelineStatus(
        nome="tjro_juris",
        observacao="present",
        encontrado=bool(entries),
        total=len(entries),
        contagens={"enviados": uploaded, "pendentes": len(entries) - uploaded},
        ultima_atualizacao=ultima_atualizacao or None,
        fonte="manifest_publicado",
        canonica=True,
        publicacao_observacao=clock_state,
        ultima_publicacao=last_publication,
        publicacao_aviso=clock_warning,
    )


def _stj_acordaos_status() -> PipelineStatus:
    try:
        text = stj_acordaos_archive.read_manifest_text()
    except httpx.HTTPError as exc:
        return PipelineStatus(
            nome="stj_acordaos",
            observacao="unavailable",
            encontrado=False,
            total=0,
            contagens={},
            fonte="manifest_publicado",
            canonica=True,
            publicacao_observacao="unavailable",
            publicacao_aviso="O manifest autoritativo não pôde ser verificado.",
            aviso=(
                "Não foi possível verificar o manifest STJ publicado; "
                f"isso não significa dataset vazio: {exc}"
            ),
        )
    if text is None:
        return PipelineStatus(
            nome="stj_acordaos",
            observacao="absent",
            encontrado=False,
            total=0,
            contagens={},
            fonte="manifest_publicado",
            canonica=True,
            publicacao_observacao="absent",
            aviso="Nenhum manifest STJ foi publicado no Internet Archive.",
        )
    manifest = ManifestSTJ(Path("stj-manifest-publicado.csv"))
    try:
        count = manifest.load_text(
            text,
            source=stj_acordaos_archive.MANIFEST_DOWNLOAD_URL,
            strict=True,
        )
    except StjManifestFormatError as exc:
        clock_state, last_publication, clock_warning = _published_object_clock(
            stj_acordaos_archive.MANIFEST_DOWNLOAD_URL
        )
        return PipelineStatus(
            nome="stj_acordaos",
            observacao="unavailable",
            encontrado=False,
            total=0,
            contagens={},
            fonte="manifest_publicado",
            canonica=True,
            publicacao_observacao=clock_state,
            ultima_publicacao=last_publication,
            publicacao_aviso=clock_warning,
            aviso=f"O manifest STJ publicado existe, mas é inválido: {exc}",
        )
    rows = manifest.to_df() if count else []
    uploaded = sum(1 for row in rows if row["ia_status"] == "uploaded")
    ultima_atualizacao = max(
        (row["updated_at"] for row in rows if row["updated_at"]),
        default="",
    )
    clock_state, last_publication, clock_warning = _published_object_clock(
        stj_acordaos_archive.MANIFEST_DOWNLOAD_URL
    )
    return PipelineStatus(
        nome="stj_acordaos",
        observacao="present",
        encontrado=bool(rows),
        total=count,
        contagens={"enviados": uploaded, "pendentes": count - uploaded},
        ultima_atualizacao=ultima_atualizacao or None,
        fonte="manifest_publicado",
        canonica=True,
        publicacao_observacao=clock_state,
        ultima_publicacao=last_publication,
        publicacao_aviso=clock_warning,
    )


def _datajud_status() -> PipelineStatus:
    try:
        published = datajud_state.read_remote_state(DEFAULT_TRIBUNAL)
    except datajud_state.RemoteStateError as exc:
        return PipelineStatus(
            nome="datajud",
            observacao="unavailable",
            encontrado=False,
            total=0,
            contagens={},
            fonte="bundle_publicado",
            canonica=True,
            publicacao_observacao="unavailable",
            publicacao_aviso="A geração DataJud autoritativa não pôde ser verificada.",
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
            publicacao_observacao="absent",
            aviso="Nenhuma geração coerente DataJud foi publicada para este tribunal.",
        )

    publication_state: _ClockState = "present" if published.published_at else "unknown"
    publication_warning = None
    if not published.published_at:
        publication_warning = (
            "Esta geração antecede o campo published_at; o horário de publicação não pode ser "
            "inferido de consultado_em ou de outro relógio."
        )

    try:
        manifest = ManifestDataJud.load_text(
            published.manifest_text,
            source=datajud_state.bundle_name(DEFAULT_TRIBUNAL),
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
            publicacao_observacao=publication_state,
            ultima_publicacao=published.published_at or None,
            publicacao_aviso=publication_warning,
            aviso=f"A geração publicada existe, mas seu manifest é inválido: {exc}",
        )

    entries = manifest.all_entries()
    ok = sum(1 for entry in entries if entry.status == STATUS_OK)
    com_docs = sum(1 for entry in entries if entry.status == STATUS_OK and entry.docs > 0)
    ultima_atualizacao = max(
        (entry.consultado_em for entry in entries if entry.consultado_em),
        default="",
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
        publicacao_observacao=publication_state,
        ultima_publicacao=published.published_at or None,
        publicacao_aviso=publication_warning,
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
    """Resolve typed product metadata to authority loaders and execution clocks."""
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

        execution = workflow_runs.observe_workflow_runs(item.workflow)
        result = result.model_copy(
            update={
                "execucao_observacao": execution.observacao,
                "ultima_tentativa": execution.ultima_tentativa,
                "ultimo_sucesso": execution.ultimo_sucesso,
                "execucao_aviso": execution.aviso,
            }
        )
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

        O catálogo ``Pipeline`` fornece identidade estável e binding de produto.
        DJEN/TJRO JURIS/STJ/DataJud consultam a mesma autoridade publicada que
        governa sua continuidade. Tentativa, sucesso e publicação permanecem
        relógios independentes; falha individual continua virando resultado parcial.
        """
        return CausaganhaStatusResult(pipelines=_pipeline_statuses())
