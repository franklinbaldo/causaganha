"""``stj_acordaos_status`` (RFC 0013 Fase 3A, RFC 0014 M1)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from stj_acordaos import service


if TYPE_CHECKING:
    from fastmcp import FastMCP


class StjAcordaosStatusResult(BaseModel):
    """Resumo do manifest local de acórdãos do STJ."""

    encontrado: bool = Field(
        description="False quando o manifest não existe ou não tem nenhuma entrada."
    )
    total: int = Field(
        default=0, description="Total de arquivos (ZIPs, JSONs mensais, parquet) registrados."
    )
    enviados: int = Field(default=0, description="Arquivos já enviados para o Internet Archive.")
    pendentes: int = Field(
        default=0, description="Arquivos baixados/construídos mas ainda não enviados."
    )
    ultima_atualizacao: str | None = Field(
        default=None,
        description="Timestamp (ISO 8601) da entrada mais recentemente atualizada no "
        "manifest, ou None quando não há nenhuma entrada.",
    )
    fonte: Literal["manifest_local"] = Field(
        default="manifest_local", description="Este manifest local é a fonte dos dados."
    )
    canonica: bool = Field(
        default=True,
        description="True: este manifest é a própria fonte de verdade do pipeline STJ "
        "acórdãos (não há um artefato remoto canônico separado dele).",
    )
    aviso: str | None = Field(default=None, description="Ressalva relevante, quando houver.")


def register(mcp: FastMCP) -> None:
    """Registra ``stj_acordaos_status`` em *mcp*."""

    @mcp.tool(
        name="stj_acordaos_status",
        annotations={
            "title": "Status do manifest de acórdãos do STJ",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def stj_acordaos_status(
        manifest_path: str = str(service.DEFAULT_MANIFEST),
    ) -> StjAcordaosStatusResult:
        """Resume o manifest local de acórdãos do STJ: arquivos rastreados e progresso de envio.

        Lê o manifest CSV só do disco local — nenhuma chamada de rede,
        nenhuma credencial envolvida. Detalhes por arquivo (nome, tipo,
        status) são deliberadamente omitidos deste resumo para manter a
        resposta pequena; use o comando `status` da CLI `stj-acordaos` para
        a listagem completa. Nunca dispara um novo download ou upload; para
        isso, use os comandos `download`/`upload` da CLI `stj-acordaos`.
        `encontrado=False` (contagens zeradas) quando o manifest ainda não
        existe ou não tem entradas — não é um erro, só um pipeline vazio.

        Args:
            manifest_path: Caminho para `stj-manifest.csv`. Default
                "data/stj/stj-manifest.csv", o caminho que o workflow
                agendado usa.
        """
        result = service.manifest_summary(Path(manifest_path))
        return StjAcordaosStatusResult(
            encontrado=result.count > 0,
            total=result.count,
            enviados=result.uploaded,
            pendentes=result.pending,
            ultima_atualizacao=result.ultima_atualizacao or None,
        )
