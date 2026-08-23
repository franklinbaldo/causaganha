"""``datajud_status`` e ``datajud_facetas`` (RFC 0013 Fase 3A/3B, RFC 0014 M1)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

import httpx
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

from datajud import service, state
from datajud.client import (
    API_KEY_ENV,
    DEFAULT_TRIBUNAL,
    WIKI_ACESSO_URL,
    DataJudAuthError,
    DataJudError,
    DataJudProtocolError,
    DataJudRateLimitError,
)
from datajud.manifest import STATUS_OK, ManifestDataJud, ManifestFormatError


if TYPE_CHECKING:
    from fastmcp import FastMCP


# Orçamento interno de tempo/retry para a chamada MCP de datajud_facetas —
# NÃO é um parâmetro da tool. Os defaults do DataJudClient (timeout=90s,
# max_retries=5, backoff 2/4/8/16/30s) são calibrados para o `enrich` da
# CLI — ingestão em lote de longa duração, onde vale esperar minutos por um
# hiccup do DataJud. Uma chamada MCP interativa tem outro orçamento: um
# timeout azarado poderia deixar esta tool aberta por ~10 minutos antes de
# produzir o ToolError (RFC 0013 Fase 3B review) — tempo longo o bastante
# para o host desistir de esperar. Estes números trocam parte dessa
# resiliência de ingestão por um pior caso — 2 tentativas * 15s de timeout
# + ~1s de backoff — que fica bem abaixo de meio minuto.
_FACETAS_TIMEOUT = 15.0
_FACETAS_MAX_RETRIES = 1
_FACETAS_BACKOFF_BASE = 1.0

# Segunda camada de defesa, independente: o deadline nativo do FastMCP na
# tool (`@mcp.tool(timeout=...)`, via `anyio.fail_after`, que vira um
# McpError → ToolError genérico, não uma das mensagens tratadas de
# `_facetas_tool_error`). O orçamento acima só limita o retry loop do
# DataJudClient; este limita a chamada inteira, incluindo qualquer
# travamento que o timeout do próprio client não cubra. Definido
# confortavelmente acima do pior caso do orçamento do client (~31s) para
# continuar sendo um backstop: o caminho comum de falha deve resolver via
# as mensagens tratadas do client antes deste disparar.
_FACETAS_TOOL_TIMEOUT = 45.0


class DatajudArtifact(BaseModel):
    """Identidade verificável de um artefato dentro da geração publicada."""

    sha256: str = Field(description="SHA-256 do artefato na geração coerente.")
    size: int = Field(description="Tamanho em bytes do artefato na geração coerente.")


class DatajudStatusResult(BaseModel):
    """Resumo do estado DataJud, publicado por default ou local por opt-in."""

    encontrado: bool = Field(
        description="False somente quando a fonte escolhida não contém estado algum."
    )
    tribunal: str = Field(
        default=DEFAULT_TRIBUNAL, description="Tribunal representado pelo estado."
    )
    total: int = Field(default=0, description="CNJs consultados até agora.")
    ok: int = Field(default=0, description="CNJs cuja última consulta teve sucesso.")
    com_docs: int = Field(default=0, description="CNJs consultados com pelo menos um documento.")
    sem_docs: int = Field(
        default=0, description="CNJs consultados sem nenhum documento encontrado."
    )
    com_erro: int = Field(default=0, description="CNJs cuja última consulta falhou.")
    ultima_atualizacao: str | None = Field(
        default=None,
        description="Timestamp (ISO 8601) da consulta mais recente registrada no manifest.",
    )
    publicado_em: str | None = Field(
        default=None,
        description="Timestamp de criação/publicação da geração, quando registrado pelo bundle.",
    )
    geracao: str | None = Field(
        default=None,
        description="Identidade content-addressed da geração coerente publicada.",
    )
    artefatos: dict[str, DatajudArtifact] = Field(
        default_factory=dict,
        description="Hashes e tamanhos dos artefatos pertencentes à mesma geração.",
    )
    fonte: Literal["bundle_publicado", "manifest_local"] = Field(
        default="bundle_publicado",
        description="Proveniência do status: geração publicada ou manifest local de trabalho.",
    )
    canonica: bool = Field(
        default=True,
        description=(
            "True somente para o bundle remoto coerente que governa continuidade do pipeline."
        ),
    )
    aviso: str | None = Field(default=None, description="Ressalva relevante, quando houver.")


class DatajudFacetaBucket(BaseModel):
    """Um grupo (bucket) da agregação retornada por ``datajud_facetas``."""

    chave: str = Field(description="Valor da faceta (ex.: nome de uma classe ou assunto).")
    qtd: int = Field(description="Quantidade de documentos com esse valor.")


class DatajudFacetasResult(BaseModel):
    """Agregação do acervo de um tribunal por uma dimensão do DataJud."""

    tribunal: str = Field(description="Tribunal consultado, normalizado em minúsculas.")
    por: str = Field(description="Dimensão usada na agregação.")
    total: int = Field(
        description="Total de documentos no acervo do tribunal — todos os valores da "
        "faceta, não só os grupos retornados abaixo."
    )
    grupos: list[DatajudFacetaBucket] = Field(
        description="Principais valores da faceta por quantidade de documentos, maior primeiro."
    )
    consultado_em: str = Field(
        description="Timestamp (ISO 8601) desta própria consulta — não há manifest local "
        "para datajud_facetas, então não existe um 'última atualização' persistido."
    )


def _manifest_summary(manifest: ManifestDataJud) -> service.ManifestStatus | None:
    entries = manifest.all_entries()
    if not entries:
        return None
    ok = sum(1 for entry in entries if entry.status == STATUS_OK)
    com_docs = sum(1 for entry in entries if entry.status == STATUS_OK and entry.docs > 0)
    ultima_atualizacao = max(
        (entry.consultado_em for entry in entries if entry.consultado_em), default=""
    )
    return service.ManifestStatus(
        total=len(entries),
        ok=ok,
        com_docs=com_docs,
        ultima_atualizacao=ultima_atualizacao,
    )


def _status_result(
    summary: service.ManifestStatus | None,
    *,
    tribunal: str,
    fonte: Literal["bundle_publicado", "manifest_local"],
    canonica: bool,
    publicado_em: str | None = None,
    geracao: str | None = None,
    artefatos: dict[str, DatajudArtifact] | None = None,
    aviso: str | None = None,
) -> DatajudStatusResult:
    if summary is None:
        return DatajudStatusResult(
            encontrado=False,
            tribunal=tribunal.lower(),
            fonte=fonte,
            canonica=canonica,
            publicado_em=publicado_em,
            geracao=geracao,
            artefatos=artefatos or {},
            aviso=aviso,
        )
    return DatajudStatusResult(
        encontrado=True,
        tribunal=tribunal.lower(),
        total=summary.total,
        ok=summary.ok,
        com_docs=summary.com_docs,
        sem_docs=summary.sem_docs,
        com_erro=summary.com_erro,
        ultima_atualizacao=summary.ultima_atualizacao or None,
        publicado_em=publicado_em,
        geracao=geracao,
        artefatos=artefatos or {},
        fonte=fonte,
        canonica=canonica,
        aviso=aviso,
    )


def _facetas_tool_error(exc: Exception) -> ToolError:
    """Mapeia a taxonomia de erro do client DataJud para um ``ToolError`` estruturado."""
    if isinstance(exc, DataJudAuthError):
        return ToolError(
            "O DataJud rejeitou a chave de API configurada (HTTP 401). É um "
            "problema de credencial do operador, não algo que se resolve "
            f"tentando de novo — busque uma chave atual em {WIKI_ACESSO_URL} "
            f"e configure a variável de ambiente {API_KEY_ENV}."
        )
    if isinstance(exc, DataJudRateLimitError):
        return ToolError(
            "O DataJud limitou esta requisição além do orçamento de retry. "
            "Recuperável: espere um pouco e chame datajud_facetas de novo."
        )
    if isinstance(exc, DataJudProtocolError):
        return ToolError(f"O DataJud retornou uma resposta não interpretável: {exc}")
    if isinstance(exc, httpx.TimeoutException | httpx.TransportError):
        return ToolError(
            "Erro de rede ao acessar o DataJud (timeout ou falha de conexão). "
            "Recuperável: tente datajud_facetas de novo; se persistir, a "
            "própria API do DataJud pode estar fora do ar."
        )
    if isinstance(exc, httpx.HTTPStatusError):
        return ToolError(f"O DataJud retornou HTTP {exc.response.status_code} para esta consulta.")
    # Deliberadamente não interpola str(exc): um DataJudError puro aqui é o
    # ramo de erro de ES não-transiente de DataJudClient._search_once, cuja
    # mensagem embute o payload cru do Elasticsearch — não é algo para
    # prometer como mensagem pública estável e segura. A causa real continua
    # disponível via `raise ... from exc` para logs/depuração.
    return ToolError(
        "O DataJud não conseguiu concluir esta agregação. Tente de novo mais "
        "tarde; se persistir, a consulta upstream pode estar indisponível."
    )


def register(mcp: FastMCP) -> None:
    """Registra ``datajud_status`` e ``datajud_facetas`` em *mcp*."""

    @mcp.tool(
        name="datajud_status",
        annotations={
            "title": "Status publicado do DataJud",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    def datajud_status(
        tribunal: str = DEFAULT_TRIBUNAL,
        fonte: Literal["publicado", "local"] = "publicado",
        diretorio_dados: str = str(service.DEFAULT_DATA_DIR),
    ) -> DatajudStatusResult:
        """Resume o estado operacional do pipeline DataJud.

        Por default lê o bundle coerente publicado no Internet Archive — a
        mesma geração que runners efêmeros restauram antes de continuar o
        pipeline. Assim um MCP recém-instalado observa produção, não a ausência
        acidental de um arquivo local. A opção ``fonte='local'`` existe apenas
        para inspecionar explicitamente um diretório de trabalho.

        A fonte publicada valida hashes e generation id antes de retornar.
        Falha de rede, corrupção ou manifest inválido geram ToolError e nunca
        são convertidos em contagens zeradas. ``encontrado=False`` no modo
        publicado significa que o bundle coerente realmente não existe.

        Args:
            tribunal: Tribunal representado pelo estado, ex. ``tjro``.
            fonte: ``publicado`` (default) ou ``local`` para diagnóstico de uma
                execução neste host.
            diretorio_dados: Diretório usado somente quando ``fonte='local'``.
        """
        tribunal = tribunal.lower()
        if fonte == "local":
            summary = service.manifest_status(Path(diretorio_dados))
            return _status_result(
                summary,
                tribunal=tribunal,
                fonte="manifest_local",
                canonica=False,
                aviso=(
                    "Estado local de trabalho; não representa necessariamente a geração "
                    "publicada do pipeline."
                ),
            )

        try:
            published = state.read_remote_state(tribunal)
        except state.RemoteStateError as exc:
            message = (
                "Não foi possível verificar o estado DataJud publicado. A produção remota "
                "pode estar indisponível ou inconsistente; isso não significa dataset vazio."
            )
            raise ToolError(message) from exc
        if published is None:
            return _status_result(
                None,
                tribunal=tribunal,
                fonte="bundle_publicado",
                canonica=True,
                aviso="Nenhuma geração coerente DataJud foi publicada para este tribunal.",
            )

        try:
            manifest = ManifestDataJud.load_text(
                published.manifest_text,
                source=state.bundle_name(tribunal),
            )
        except ManifestFormatError as exc:
            message = (
                "A geração DataJud publicada passou pela verificação de bytes, mas seu "
                "manifest não pôde ser interpretado."
            )
            raise ToolError(message) from exc
        artifacts = {
            name: DatajudArtifact(sha256=str(meta["sha256"]), size=int(meta["size"]))
            for name, meta in published.files.items()
        }
        warning = None
        if not published.published_at:
            warning = (
                "Esta geração foi publicada antes de o bundle registrar timestamp de publicação; "
                "use ultima_atualizacao como sinal temporal do conteúdo."
            )
        return _status_result(
            _manifest_summary(manifest),
            tribunal=tribunal,
            fonte="bundle_publicado",
            canonica=True,
            publicado_em=published.published_at or None,
            geracao=published.generation,
            artefatos=artifacts,
            aviso=warning,
        )

    @mcp.tool(
        name="datajud_facetas",
        timeout=_FACETAS_TOOL_TIMEOUT,
        annotations={
            "title": "Agregação por faceta no DataJud",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def datajud_facetas(
        tribunal: str = DEFAULT_TRIBUNAL,
        por: Literal["classe", "assunto", "orgao", "grau", "sistema"] = "classe",
        limite: Annotated[
            int, Field(ge=1, le=100, description="Máximo de grupos a retornar.")
        ] = 15,
    ) -> DatajudFacetasResult:
        """Agrega o acervo de DataJud de um tribunal por uma dimensão (classe, assunto, ...).

        Consulta a API pública do DataJud ao vivo (chamada de rede, ao
        contrário do modo local de `datajud_status`) para contar documentos
        agrupados por *por*, sem baixar nenhum documento. Use para responder
        perguntas como "quais são as 10 principais classes no acervo do TJRO?"
        sem buscar ou enriquecer processos individuais. Retorna o total do
        acervo inteiro mais os `limite` grupos com mais documentos.
        Um orçamento interno de tempo mais apertado que o do `datajud enrich`
        da CLI, mais um deadline rígido por chamada, mantêm o pior caso bem
        abaixo de um minuto, não minutos.

        Args:
            tribunal: Tribunal a consultar, minúsculo (ex.: "tjro"). Default
                o mesmo tribunal que a CLI `datajud` usa por padrão.
            por: Dimensão da agregação.
            limite: Máximo de grupos a retornar, 1-100. O campo `total`
                sempre reflete o acervo inteiro, mesmo quando `limite`
                corta a lista de grupos.
        """
        try:
            total, buckets = await service.facetas(
                tribunal,
                por,
                limite,
                request_timeout=_FACETAS_TIMEOUT,
                max_retries=_FACETAS_MAX_RETRIES,
                backoff_base=_FACETAS_BACKOFF_BASE,
            )
        except (DataJudError, httpx.HTTPError) as exc:
            raise _facetas_tool_error(exc) from exc
        return DatajudFacetasResult(
            tribunal=tribunal.lower(),
            por=por,
            total=total,
            grupos=[
                DatajudFacetaBucket(chave=bucket["chave"], qtd=bucket["qtd"]) for bucket in buckets
            ],
            consultado_em=datetime.now(UTC).isoformat(timespec="seconds"),
        )
