"""``djen_backup_status`` (RFC 0013 Fase 3A, RFC 0014 M1)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from djen_backup import service


if TYPE_CHECKING:
    from fastmcp import FastMCP


_CANONICAL_NOTE = (
    "Origem local, não canônica: a fonte de verdade do DJEN é o "
    "sync-manifest.parquet no Internet Archive (ver "
    "docs/planning/manifest-source-of-truth.md) — este manifest local "
    "pode estar atrasado em relação a ele."
)


class DjenBackupStatusResult(BaseModel):
    """Resumo do manifest local de sincronização do DJEN."""

    encontrado: bool = Field(
        description="False quando o manifest não existe ou não tem nenhuma entrada."
    )
    total: int = Field(default=0, description="Total de pares (tribunal, data) registrados.")
    enviados: int = Field(default=0, description="Entradas já enviadas para o Internet Archive.")
    disponiveis: int = Field(
        default=0, description="Entradas confirmadas disponíveis no DJEN, aguardando envio."
    )
    ausentes: int = Field(
        default=0, description="Entradas confirmadas ausentes no DJEN (sem publicação)."
    )
    desconhecidos: int = Field(
        default=0, description="Entradas ainda não verificadas contra o DJEN."
    )
    ultima_atualizacao: str | None = Field(
        default=None,
        description="Timestamp (ISO 8601) da entrada mais recentemente atualizada no "
        "manifest, ou None quando não há nenhuma entrada.",
    )
    fonte: Literal["cache_local"] = Field(
        default="cache_local",
        description="Cache local nesta máquina — não é a fonte canônica (ver `canonica`).",
    )
    canonica: Literal[False] = Field(
        default=False,
        description="Sempre False: a fonte de verdade do DJEN é o parquet no Internet "
        "Archive, não este manifest local (ver `aviso`).",
    )
    aviso: str | None = Field(default=_CANONICAL_NOTE, description="Ressalva relevante.")


def register(mcp: FastMCP) -> None:
    """Registra ``djen_backup_status`` em *mcp*."""

    @mcp.tool(
        name="djen_backup_status",
        annotations={
            "title": "Status do manifest de sincronização do DJEN",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def djen_backup_status(
        manifest_file: str = str(service.DEFAULT_MANIFEST_FILE),
    ) -> DjenBackupStatusResult:
        """Resume o manifest local de sincronização do DJEN: cobertura por tribunal e data.

        Lê `sync-manifest.csv` só do disco local — nenhuma chamada de rede,
        nenhum fetch ao IA, nenhuma credencial envolvida. A fonte canônica
        é o `sync-manifest.parquet` no Internet Archive (ver
        `docs/planning/manifest-source-of-truth.md`); esta tool só vê o
        cache CSV local que já existe nesta máquina, que pode estar
        atrasado em relação ao IA — daí `canonica=False` e o `aviso` no
        retorno. Nunca dispara uma sincronização, upload ou reset; para
        isso, use a CLI `djen-backup`. `encontrado=False` (contagens
        zeradas) quando o manifest ainda não existe ou não tem entradas.

        Args:
            manifest_file: Caminho para o CSV do manifest local. Default
                "data/sync-manifest.csv".
        """
        result = service.manifest_status(Path(manifest_file))
        return DjenBackupStatusResult(
            encontrado=result.total > 0,
            total=result.total,
            enviados=result.uploaded,
            disponiveis=result.available,
            ausentes=result.absent,
            desconhecidos=result.unknown,
            ultima_atualizacao=result.ultima_atualizacao or None,
        )
