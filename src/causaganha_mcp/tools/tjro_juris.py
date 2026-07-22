"""``tjro_juris_status`` (RFC 0013 Fase 3A, RFC 0014 M1)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from tjro_juris import service


if TYPE_CHECKING:
    from fastmcp import FastMCP


# tjro_juris.service não tem uma constante DEFAULT_DATA_DIR — a CLI recebe
# data_dir como argumento posicional obrigatório. Isso replica o argv literal
# que tjro-sync.yml usa ("tjro-juris crawl data/tjro-juris ...").
_DEFAULT_DATA_DIR = "data/tjro-juris"


class TjroJurisStatusResult(BaseModel):
    """Resumo do manifest local do TJRO JURIS."""

    encontrado: bool = Field(
        description="False quando o manifest não existe ou não tem nenhuma entrada."
    )
    total: int = Field(default=0, description="Total de janelas (tipo, mês/ano) registradas.")
    enviados: int = Field(default=0, description="Janelas já enviadas para o Internet Archive.")
    pendentes: int = Field(default=0, description="Janelas coletadas mas ainda não enviadas.")
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
        description="True: este manifest é a própria fonte de verdade do pipeline TJRO "
        "JURIS (não há um artefato remoto canônico separado dele).",
    )
    aviso: str | None = Field(default=None, description="Ressalva relevante, quando houver.")


def register(mcp: FastMCP) -> None:
    """Registra ``tjro_juris_status`` em *mcp*."""

    @mcp.tool(
        name="tjro_juris_status",
        annotations={
            "title": "Status do manifest do TJRO JURIS",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def tjro_juris_status(diretorio_dados: str = _DEFAULT_DATA_DIR) -> TjroJurisStatusResult:
        """Resume o manifest local do TJRO JURIS: janelas coletadas e progresso de envio.

        Lê `tjro-juris-manifest.csv` em `diretorio_dados`, só do disco
        local — nenhuma chamada de rede, nenhuma credencial envolvida. Use
        para checar o progresso do backfill diário do `tjro-sync.yml`
        (`--desde-ano 1988`) sem precisar de um shell. Nunca dispara uma
        nova coleta ou upload; para isso, use os comandos `crawl`/`upload`
        da CLI `tjro-juris`. `encontrado=False` (contagens zeradas) quando
        o manifest ainda não existe ou não tem entradas — não é um erro,
        só um pipeline vazio.

        Args:
            diretorio_dados: Diretório com o manifest e os parquets.
                Default "data/tjro-juris", o caminho que o workflow
                agendado usa.
        """
        result = service.manifest_status(Path(diretorio_dados))
        return TjroJurisStatusResult(
            encontrado=result.total > 0,
            total=result.total,
            enviados=result.uploaded,
            pendentes=result.pending,
            ultima_atualizacao=result.ultima_atualizacao or None,
        )
