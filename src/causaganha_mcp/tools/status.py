"""``causaganha_status`` — panorama agregado dos quatro pipelines (RFC 0014 M1).

Chama `service.py` de cada pacote diretamente (`datajud.service`,
`tjro_juris.service`, `stj_acordaos.service`, `djen_backup.service`) — nunca
as tools `*_status` através do próprio protocolo MCP. Ir por dentro do
protocolo para montar uma resposta que o próprio protocolo vai servir de
novo seria indireção sem propósito, e acoplaria esta tool ao registro de
tools do servidor em vez de à camada de serviço (RFC 0014 §3).

Cada pipeline aparece com `total` (comum, sem interpretação) e `contagens`
— um dict específico do pipeline, com os mesmos nomes de campo que a tool
`*_status` correspondente já usa. Não existe um "concluído"/"pendente"
genérico: mapear isso teria exigido decidir, por exemplo, se uma entrada
`ausente` do DJEN conta como concluída ou pendente — uma interpretação de
negócio que a RFC 0014 explicitamente não autoriza ainda (§3: "sem
saudável/degradado", só fatos).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

import datajud.service as datajud_service
import djen_backup.service as djen_backup_service
import stj_acordaos.service as stj_acordaos_service
import tjro_juris.service as tjro_juris_service


if TYPE_CHECKING:
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
    except OSError as exc:
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
    except OSError as exc:
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
        """Panorama dos quatro pipelines locais (DJEN, TJRO JURIS, STJ, DataJud) numa só chamada.

        Chama a mesma camada de serviço que `djen_backup_status`,
        `tjro_juris_status`, `stj_acordaos_status` e `datajud_status` usam
        individualmente — não invoca essas tools via protocolo MCP. Um
        pipeline sem manifest nesta máquina aparece com `encontrado=False`
        e contagens vazias; isso nunca falha a chamada inteira, mesmo que
        outros pipelines tenham dado.

        Não retorna um veredito de saúde ("saudável"/"degradado") — só
        fatos: total, contagens específicas do pipeline, quando foi
        atualizado pela última vez, se a fonte é o próprio manifest ou um
        cache que pode estar atrasado, e uma ressalva quando existir. Para
        contagens detalhadas por pipeline, prefira a tool `<pipeline>_status`
        individual — esta é um resumo amplo, não um substituto.
        """
        return CausaganhaStatusResult(
            pipelines=[
                _djen_status(),
                _tjro_juris_status(),
                _stj_acordaos_status(),
                _datajud_status(),
            ]
        )
