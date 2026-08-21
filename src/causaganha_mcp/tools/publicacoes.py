"""``publicacoes_buscar`` — busca semântica no arquivo público DJEN do CausaGanha."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

from causaganha.publicacoes import service
from causaganha.publicacoes.models import (
    AcervoIndisponivelError,
    CatalogoIndisponivelError,
    CriteriosInvalidosError,
    PublicacoesBusca,
)


if TYPE_CHECKING:
    from fastmcp import FastMCP


_PUBLICACOES_TOOL_TIMEOUT = 60.0


class PublicacaoResult(BaseModel):
    """Uma publicação preservada no arquivo público do CausaGanha."""

    id: str
    data: str | None = None
    tribunal: str | None = None
    tipo: str | None = None
    orgao: str | None = None
    cnj: str | None = None
    cnj_formatado: str | None = None
    tipo_documento: str | None = None
    classe: str | None = None
    trecho: str | None = Field(
        default=None,
        description="Até 500 caracteres quando `incluir_trecho=True` ou a busca depende de texto.",
    )
    url: str | None = Field(default=None, description="Link publicado pela fonte, quando houver.")
    ia_item: str | None = Field(
        default=None,
        description="Identidade do item público do Internet Archive que preserva o registro.",
    )
    natureza: Literal["arquivo"] = "arquivo"
    fonte: Literal["CausaGanha / DJEN arquivado / Internet Archive"] = (
        "CausaGanha / DJEN arquivado / Internet Archive"
    )


class CoberturaResult(BaseModel):
    """Cobertura conhecida do recorte consultado."""

    status: Literal["sem_lacuna_conhecida", "parcial", "desconhecida", "insuficiente"]
    lacunas_conhecidas: int | None = None
    arquivos_consultados: int
    itens_consultados: int
    aviso: str | None = None


class ProximaAcaoResult(BaseModel):
    """Próxima operação semântica útil para um agente."""

    quando: str
    acao: str
    tool: str
    argumentos: dict[str, str | bool | int] = Field(default_factory=dict)


class PublicacoesBuscarResult(BaseModel):
    """Resultado de uma busca no arquivo DJEN preservado pelo CausaGanha."""

    resumo: str
    total_encontrado: int
    resultados: list[PublicacaoResult] = Field(default_factory=list)
    pagina: int
    limite: int
    resultados_truncados: bool
    cobertura: CoberturaResult
    criterios: dict[str, str | bool | int | None]
    consultado_em: str
    natureza: Literal["arquivo"] = "arquivo"
    fonte: Literal["CausaGanha / DJEN arquivado / Internet Archive"] = (
        "CausaGanha / DJEN arquivado / Internet Archive"
    )
    avisos: list[str] = Field(default_factory=list)
    next_actions: list[ProximaAcaoResult] = Field(default_factory=list)


def _next_actions(result: PublicacoesBusca) -> list[ProximaAcaoResult]:
    cnjs = sorted({item.numero_processo for item in result.resultados if item.numero_processo})
    if len(cnjs) != 1:
        return []
    cnj = cnjs[0]
    return [
        ProximaAcaoResult(
            quando="Se você precisa do contexto multi-fonte preservado deste processo.",
            acao="Consultar o dossiê arquivado do CNJ.",
            tool="processo_consultar",
            argumentos={"cnj": cnj},
        ),
        ProximaAcaoResult(
            quando="Se a pergunta é sobre o andamento processual atual, não apenas publicações arquivadas.",
            acao="Consultar o estado processual live.",
            tool="processo_estado",
            argumentos={"cnj": cnj},
        ),
    ]


def _to_result(result: PublicacoesBusca) -> PublicacoesBuscarResult:
    if result.total_encontrado:
        resumo = (
            f"O arquivo do CausaGanha encontrou {result.total_encontrado} publicação(ões) "
            f"para os critérios informados; esta resposta mostra {len(result.resultados)}."
        )
    elif result.cobertura.status in {"parcial", "desconhecida", "insuficiente"}:
        resumo = (
            "Nenhuma publicação foi localizada no recorte consultável, mas a cobertura não permite "
            "tratar esse zero como prova de ausência."
        )
    else:
        resumo = "Nenhuma publicação foi localizada no arquivo para os critérios informados."

    return PublicacoesBuscarResult(
        resumo=resumo,
        total_encontrado=result.total_encontrado,
        resultados=[
            PublicacaoResult(
                id=item.id,
                data=item.data,
                tribunal=item.tribunal,
                tipo=item.tipo,
                orgao=item.orgao,
                cnj=item.numero_processo,
                cnj_formatado=item.numero_processo_mascara,
                tipo_documento=item.tipo_documento,
                classe=item.classe,
                trecho=item.trecho,
                url=item.link,
                ia_item=item.ia_item,
            )
            for item in result.resultados
        ],
        pagina=result.pagina,
        limite=result.limite,
        resultados_truncados=result.resultados_truncados,
        cobertura=CoberturaResult(
            status=result.cobertura.status,
            lacunas_conhecidas=result.cobertura.lacunas_conhecidas,
            arquivos_consultados=result.cobertura.arquivos_consultados,
            itens_consultados=result.cobertura.itens_consultados,
            aviso=result.cobertura.aviso,
        ),
        criterios=result.criterios,
        consultado_em=result.consultado_em,
        avisos=result.avisos,
        next_actions=_next_actions(result),
    )


def _tool_error(exc: Exception) -> ToolError:
    if isinstance(exc, CriteriosInvalidosError):
        return ToolError(str(exc))
    if isinstance(exc, CatalogoIndisponivelError):
        return ToolError(
            "Não foi possível consultar o catálogo público do CausaGanha no Internet Archive. "
            "Tente novamente mais tarde."
        )
    if isinstance(exc, AcervoIndisponivelError):
        return ToolError(
            "O catálogo foi localizado, mas um ou mais Parquets necessários ficaram indisponíveis "
            "durante a consulta. Tente novamente mais tarde."
        )
    return ToolError("Não foi possível concluir a busca no arquivo público do CausaGanha.")


def register(mcp: FastMCP) -> None:
    """Registra a busca archive-first de publicações."""

    @mcp.tool(
        name="publicacoes_buscar",
        timeout=_PUBLICACOES_TOOL_TIMEOUT,
        annotations={
            "title": "Busca publicações judiciais no arquivo público do CausaGanha",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    def publicacoes_buscar(
        processo: str | None = None,
        oab: str | None = None,
        uf_oab: str | None = None,
        parte: str | None = None,
        advogado: str | None = None,
        texto: str | None = None,
        tribunal: str | None = None,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        incluir_trecho: bool = False,
        limite: Annotated[int, Field(ge=1, le=50)] = 10,
        pagina: Annotated[int, Field(ge=1, le=1000)] = 1,
    ) -> PublicacoesBuscarResult:
        """Busca publicações preservadas por processo, OAB, pessoa, texto, tribunal ou período.

        Use esta tool para responder **o que o arquivo público do CausaGanha preservou** do DJEN.
        Ela consulta diretamente os Parquets canônicos publicados no Internet Archive; o agente não
        precisa conhecer catálogo, tabelas, joins, DuckDB ou nomes de arquivos. A API live do DJEN
        não é consultada e nunca funciona como fallback silencioso.

        Para contexto multi-fonte de um CNJ use `processo_consultar`. Para andamento atual use
        `processo_estado`. Zero resultados só é forte quando a própria resposta qualifica a cobertura.
        `incluir_trecho=True` custa mais porque consulta também o Parquet de textos; deixe False quando
        metadados e identidade da publicação forem suficientes.
        """
        try:
            result = service.buscar_publicacoes(
                processo=processo,
                oab=oab,
                uf_oab=uf_oab,
                parte=parte,
                advogado=advogado,
                texto=texto,
                tribunal=tribunal,
                data_inicio=data_inicio,
                data_fim=data_fim,
                incluir_trecho=incluir_trecho,
                limite=limite,
                pagina=pagina,
            )
        except (
            CriteriosInvalidosError,
            CatalogoIndisponivelError,
            AcervoIndisponivelError,
        ) as exc:
            raise _tool_error(exc) from exc
        return _to_result(result)
