"""``causaganha_status`` — panorama agregado dos quatro pipelines (RFC 0014 M1).

Os fatos de cada pipeline continuam vindo diretamente de sua autoridade já
estabelecida. A identidade estável do produto — nome, pacote, fonte e tool de
status — vem da relação tipada ``Pipeline`` em ``knowledge/``. Não há chamada
MCP recursiva e nenhum contrato físico de dados foi movido para Markdown.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import httpx
from pydantic import BaseModel, Field

from causaganha_mcp import knowledge
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
    aviso: str | None = Field(default=None, description="Ressalva relevante, quando houver.")


class CausaganhaStatusResult(BaseModel):
    """Panorama agregado dos quatro pipelines do CausaGanha."""

    pipelines: list[PipelineStatus] = Field(
        description="Um item por pipeline: djen, tjro_juris, stj_acordaos, datajud."
    )


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
    )


def _tjro_juris_status() -> PipelineStatus:
    try:
        text = tjro_juris_archive.read_manifest_text()
    except httpx.HTTPError as exc:
        return PipelineStatus(nome="tjro_juris", observacao="unavailable", encontrado=False, total=0, contagens={}, fonte="manifest_publicado", canonica=True, aviso=("Não foi possível verificar o manifest TJRO JURIS publicado; " f"isso não significa dataset vazio: {exc}"))
    if text is None:
        return PipelineStatus(nome="tjro_juris", observacao="absent", encontrado=False, total=0, contagens={}, fonte="manifest_publicado", canonica=True, aviso="Nenhum manifest TJRO JURIS foi publicado no Internet Archive.")
    try:
        manifest = ManifestJuris.load_text(text, source=tjro_juris_archive.MANIFEST_DOWNLOAD_URL)
    except TjroJurisManifestFormatError as exc:
        return PipelineStatus(nome="tjro_juris", observacao="unavailable", encontrado=False, total=0, contagens={}, fonte="manifest_publicado", canonica=True, aviso=f"O manifest TJRO JURIS publicado existe, mas é inválido: {exc}")
    entries = manifest.all_entries()
    uploaded = sum(1 for entry in entries if entry.ia_status == "uploaded")
    ultima_atualizacao = max((entry.updated_at for entry in entries if entry.updated_at), default="")
    return PipelineStatus(nome="tjro_juris", observacao="present", encontrado=bool(entries), total=len(entries), contagens={"enviados": uploaded, "pendentes": len(entries) - uploaded}, ultima_atualizacao=ultima_atualizacao or None, fonte="manifest_publicado", canonica=True)


def _stj_acordaos_status() -> PipelineStatus:
    try:
        text = stj_acordaos_archive.read_manifest_text()
    except httpx.HTTPError as exc:
        return PipelineStatus(nome="stj_acordaos", observacao="unavailable", encontrado=False, total=0, contagens={}, fonte="manifest_publicado", canonica=True, aviso=("Não foi possível verificar o manifest STJ publicado; " f"isso não significa dataset vazio: {exc}"))
    if text is None:
        return PipelineStatus(nome="stj_acordaos", observacao="absent", encontrado=False, total=0, contagens={}, fonte="manifest_publicado", canonica=True, aviso="Nenhum manifest STJ foi publicado no Internet Archive.")
    manifest = ManifestSTJ(Path("stj-manifest-publicado.csv"))
    try:
        count = manifest.load_text(text, source=stj_acordaos_archive.MANIFEST_DOWNLOAD_URL, strict=True)
    except StjManifestFormatError as exc:
        return PipelineStatus(nome="stj_acordaos", observacao="unavailable", encontrado=False, total=0, contagens={}, fonte="manifest_publicado", canonica=True, aviso=f"O manifest STJ publicado existe, mas é inválido: {exc}")
    rows = manifest.to_df() if count else []
    uploaded = sum(1 for row in rows if row["ia_status"] == "uploaded")
    ultima_atualizacao = max((row["updated_at"] for row in rows if row["updated_at"]), default="")
    return PipelineStatus(nome="stj_acordaos", observacao="present", encontrado=bool(rows), total=count, contagens={"enviados": uploaded, "pendentes": count - uploaded}, ultima_atualizacao=ultima_atualizacao or None, fonte="manifest_publicado", canonica=True)


def _datajud_status() -> PipelineStatus:
    try:
        published = datajud_state.read_remote_state(DEFAULT_TRIBUNAL)
    except datajud_state.RemoteStateError as exc:
        return PipelineStatus(nome="datajud", observacao="unavailable", encontrado=False, total=0, contagens={}, fonte="bundle_publicado", canonica=True, aviso=("Não foi possível verificar a geração DataJud publicada; " f"isso não significa dataset vazio: {exc}"))
    if published is None:
        return PipelineStatus(nome="datajud", observacao="absent", encontrado=False, total=0, contagens={}, fonte="bundle_publicado", canonica=True, aviso="Nenhuma geração coerente DataJud foi publicada para este tribunal.")
    try:
        manifest = ManifestDataJud.load_text(published.manifest_text, source=datajud_state.bundle_name(DEFAULT_TRIBUNAL))
    except DatajudManifestFormatError as exc:
        return PipelineStatus(nome="datajud", observacao="unavailable", encontrado=False, total=0, contagens={}, publicado_em=published.published_at or None, geracao=published.generation, fonte="bundle_publicado", canonica=True, aviso=f"A geração publicada existe, mas seu manifest é inválido: {exc}")
    entries = manifest.all_entries()
    ok = sum(1 for entry in entries if entry.status == STATUS_OK)
    com_docs = sum(1 for entry in entries if entry.status == STATUS_OK and entry.docs > 0)
    ultima_atualizacao = max((entry.consultado_em for entry in entries if entry.consultado_em), default="")
    warning = None
    if not published.published_at:
        warning = "Esta geração antecede o timestamp de publicação no bundle; use ultima_atualizacao como sinal temporal do conteúdo."
    return PipelineStatus(nome="datajud", observacao="present", encontrado=bool(entries), total=len(entries), contagens={"ok": ok, "com_docs": com_docs, "sem_docs": ok - com_docs, "com_erro": len(entries) - ok}, ultima_atualizacao=ultima_atualizacao or None, publicado_em=published.published_at or None, geracao=published.generation, fonte="bundle_publicado", canonica=True, aviso=warning)


def pipeline_status_loaders() -> tuple[tuple[str, Callable[[], PipelineStatus]], ...]:
    """Return direct in-process bindings for aggregate pipeline status."""
    return (("djen_backup_status", _djen_status), ("tjro_juris_status", _tjro_juris_status), ("stj_acordaos_status", _stj_acordaos_status), ("datajud_status", _datajud_status))


def _pipeline_statuses(metadata: tuple[knowledge.PipelineMetadata, ...] | None = None) -> list[PipelineStatus]:
    """Resolve the typed OKF product catalog to established direct loaders."""
    declared = metadata if metadata is not None else knowledge.load_pipeline_metadata()
    by_tool = {item.mcp_status: item for item in declared}
    if len(by_tool) != len(declared):
        raise RuntimeError("knowledge Pipeline relation contains duplicate mcp_status values")
    bindings = pipeline_status_loaders()
    expected_tools = {tool for tool, _loader in bindings}
    declared_tools = set(by_tool)
    if declared_tools != expected_tools:
        missing = sorted(expected_tools - declared_tools)
        unknown = sorted(declared_tools - expected_tools)
        raise RuntimeError(f"knowledge Pipeline bindings disagree with code: missing={missing}, unknown={unknown}")
    results: list[PipelineStatus] = []
    for tool_name, loader in bindings:
        item = by_tool[tool_name]
        try:
            import_module(f"{item.pacote}.service")
        except ImportError as error:
            raise RuntimeError(f"Pipeline {item.nome!r} declares unavailable package {item.pacote!r}") from error
        result = loader()
        if result.nome != item.nome:
            raise RuntimeError(f"Pipeline {item.nome!r} is bound to loader returning {result.nome!r}")
        results.append(result)
    return results


def register(mcp: FastMCP) -> None:
    """Registra ``causaganha_status`` em *mcp*."""

    @mcp.tool(name="causaganha_status", annotations={"title": "Panorama agregado dos pipelines do CausaGanha", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True})
    def causaganha_status() -> CausaganhaStatusResult:
        """Panorama dos pipelines declarados no catálogo OKF do CausaGanha.

        O catálogo ``Pipeline`` fornece identidade estável e binding de produto.
        DJEN/TJRO JURIS/STJ/DataJud consultam a mesma autoridade publicada que
        governa sua continuidade. Falha de uma fonte individual continua virando
        resultado parcial, enquanto divergência do catálogo é explícita.
        """
        return CausaganhaStatusResult(pipelines=_pipeline_statuses())
