"""``processo_consultar`` — dossiê unificado de um processo por CNJ (RFC 0014 M2).

Primeira tool MCP que serve diretamente quem quer saber sobre um processo
específico, não o operador do pipeline. Chama `causaganha.processos.service`
diretamente — nunca reimplementa a consulta aqui. Lê os parquets canônicos
do Internet Archive (`indice_processual.parquet` + os parquets de origem por
fonte); nenhum cache local nesta primeira versão (ver o módulo de serviço
para a justificativa completa).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated
from urllib.parse import quote

import duckdb
import httpx
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

from causaganha.processos import service
from causaganha.processos.models import CnjInvalidoError


if TYPE_CHECKING:
    from fastmcp import FastMCP

    from causaganha.processos.models import ProcessoConsultaResult


# Consulta de rede (parquets remotos via httpfs) mas de baixa latência — um
# lookup de linha via índice + poucas leituras de parquet de origem, não uma
# agregação de dataset inteiro (esse é o caso de datajud_facetas). O deadline
# ainda assim fica bem abaixo de um minuto, mesma disciplina de
# datajud_facetas: interativo, não ingestão.
_PROCESSO_TOOL_TIMEOUT = 30.0

_WEB_BASE_URL_ENV = "CAUSAGANHA_WEB_BASE_URL"


class FonteCoberturaResult(BaseModel):
    """Estado de uma fonte na geração do dataset."""

    fonte: str = Field(description="Nome da fonte: djen, juris, stj ou datajud.")
    status: str = Field(
        description="Como a fonte foi carregada na geração do dataset "
        "(ex.: loaded_local, loaded_remote, unavailable)."
    )
    registros: int = Field(
        description="Quantidade de processos que essa fonte contribuiu no dataset inteiro "
        "— não é uma contagem específica deste CNJ."
    )


class ProximaAcaoResult(BaseModel):
    """Próxima operação semântica útil para continuar a investigação do CNJ."""

    quando: str
    acao: str
    tool: str
    argumentos: dict[str, str | bool | int] = Field(default_factory=dict)


class DocumentoResult(BaseModel):
    """Um documento JURIS ou STJ do processo."""

    fonte: str = Field(description="'juris' ou 'stj' — nunca DJEN nem DataJud.")
    id_documento: str
    tipo: str | None = None
    data: str | None = Field(default=None, description="Data ISO (AAAA-MM-DD), quando houver.")
    url: str | None = None
    resumo: str | None = Field(
        default=None, description="Resumo truncado em 500 caracteres na reconciliação."
    )


class DjenResumoResult(BaseModel):
    """Resumo das publicações DJEN do processo."""

    primeira_publicacao: str | None = None
    ultima_publicacao: str | None = None
    n_publicacoes: int | None = None
    tribunais: list[str] = Field(default_factory=list)


class JurisDecisaoResult(BaseModel):
    """Decisão(ões) do TJRO JURIS para o processo."""

    n_documentos: int | None = None
    tipos: list[str] = Field(default_factory=list)
    data_julgamento: str | None = None
    orgao: str | None = None
    relator: str | None = None
    classe: str | None = None
    url: str | None = None


class StjAcordaoResult(BaseModel):
    """Acórdão do STJ para o processo, quando houver."""

    id: str | None = None
    classe: str | None = None
    relator: str | None = None
    tema: str | None = None
    tese: str | None = None
    ementa: str | None = None
    data_decisao: str | None = None
    data_publicacao: str | None = None


class DatajudCapaResult(BaseModel):
    """Capa oficial do DataJud (RFC 0010) para o processo."""

    classe_oficial: str | None = None
    assuntos: str | None = None
    orgao_julgador: str | None = None
    grau: str | None = None
    data_ajuizamento: str | None = None
    ultima_atualizacao: str | None = None


class ProcessoConsultarResult(BaseModel):
    """Dossiê unificado de um processo, montado a partir das fontes canônicas do IA."""

    encontrado: bool = Field(
        description="False quando o CNJ é válido mas não aparece em nenhuma fonte."
    )
    cnj: str = Field(description="CNJ normalizado, 20 dígitos.")
    cnj_formatado: str = Field(description="CNJ na máscara de exibição NNNNNNN-DD.AAAA.J.TR.OOOO.")
    fontes_presentes: list[str] = Field(
        default_factory=list,
        description="Fontes que têm registro para este CNJ (subconjunto de "
        "djen/juris/stj/datajud).",
    )
    cobertura_dataset: list[FonteCoberturaResult] = Field(
        default_factory=list,
        description="Estado de cada fonte na geração do dataset inteiro — distingue uma fonte "
        "que não tinha este CNJ de uma fonte que estava indisponível quando o dataset foi gerado.",
    )
    djen: DjenResumoResult | None = None
    juris: JurisDecisaoResult | None = None
    stj: StjAcordaoResult | None = None
    datajud: DatajudCapaResult | None = None
    documentos: list[DocumentoResult] = Field(default_factory=list)
    documentos_truncados: bool = Field(
        default=False, description="True quando há mais documentos além de `limite_documentos`."
    )
    dataset_gerado_em: str | None = Field(
        default=None,
        description="Timestamp (ISO 8601) de quando o dataset foi gerado, do relatório de "
        "cobertura — None quando o relatório está indisponível (ver `avisos`).",
    )
    consultado_em: str = Field(description="Timestamp (ISO 8601) desta própria consulta.")
    fonte: str = Field(
        default="parquet_ia",
        description="Os parquets canônicos do Internet Archive são a única fonte desta tool "
        "— não há cache local nesta primeira versão.",
    )
    canonica: bool = Field(
        default=True, description="Sempre True: a fonte já é a canônica, sem cache intermediário."
    )
    avisos: list[str] = Field(
        default_factory=list, description="Ressalvas relevantes (ex.: relatório indisponível)."
    )
    next_actions: list[ProximaAcaoResult] = Field(
        default_factory=list,
        description="Próximas consultas úteis sem executar outra fonte implicitamente.",
    )
    web_url: str | None = Field(
        default=None,
        description=f"URL completa do dossiê no dashboard web, montada apenas quando a "
        f"variável de ambiente {_WEB_BASE_URL_ENV} está configurada — None caso contrário.",
    )
    web_path: str = Field(
        description="Caminho público conhecido do dossiê: /processo?cnj=<mascarado>."
    )


def _web_path(cnj_formatado: str) -> str:
    return f"/processo?cnj={quote(cnj_formatado)}"


def _web_url(cnj_formatado: str) -> str | None:
    base = os.environ.get(_WEB_BASE_URL_ENV, "").strip()
    if not base:
        return None
    return f"{base.rstrip('/')}{_web_path(cnj_formatado)}"


def _next_actions(r: ProcessoConsultaResult) -> list[ProximaAcaoResult]:
    """Suggest explicit composition without silently crossing evidence boundaries."""
    actions = [
        ProximaAcaoResult(
            quando=(
                "Se a pergunta exige saber o andamento atual ou se houve movimento depois "
                "da geração deste snapshot."
            ),
            acao="Consultar o estado processual live no DataJud.",
            tool="processo_estado",
            argumentos={"cnj": r.nr_processo},
        ),
        ProximaAcaoResult(
            quando=(
                "Se você precisa localizar as publicações DJEN preservadas deste processo "
                "ou confirmar o detalhe de uma comunicação."
            ),
            acao="Buscar publicações arquivadas deste CNJ.",
            tool="publicacoes_buscar",
            argumentos={"processo": r.nr_processo},
        ),
    ]
    if r.stj is not None:
        actions.append(
            ProximaAcaoResult(
                quando=(
                    "Se o resumo do STJ já retornado não basta e você precisa do teor "
                    "completo do acórdão."
                ),
                acao="Buscar o teor completo do acórdão STJ deste processo.",
                tool="decisoes_buscar",
                argumentos={"cnj": r.nr_processo, "fonte": "stj"},
            )
        )
    if r.juris is not None:
        actions.append(
            ProximaAcaoResult(
                quando=(
                    "Se o resumo do TJRO JURIS já retornado não basta e você precisa do "
                    "teor completo da decisão."
                ),
                acao="Buscar o teor completo da decisão JURIS deste processo.",
                tool="decisoes_buscar",
                argumentos={"cnj": r.nr_processo, "fonte": "juris"},
            )
        )
    return actions


def _to_result(r: ProcessoConsultaResult) -> ProcessoConsultarResult:
    return ProcessoConsultarResult(
        encontrado=r.encontrado,
        cnj=r.nr_processo,
        cnj_formatado=r.nr_processo_mascara,
        fontes_presentes=r.fontes_presentes,
        cobertura_dataset=[
            FonteCoberturaResult(fonte=c.fonte, status=c.status, registros=c.registros)
            for c in r.cobertura_dataset
        ],
        djen=DjenResumoResult(
            primeira_publicacao=r.djen.primeira_publicacao,
            ultima_publicacao=r.djen.ultima_publicacao,
            n_publicacoes=r.djen.n_publicacoes,
            tribunais=r.djen.tribunais,
        )
        if r.djen
        else None,
        juris=JurisDecisaoResult(
            n_documentos=r.juris.n_documentos,
            tipos=r.juris.tipos,
            data_julgamento=r.juris.data_julgamento,
            orgao=r.juris.orgao,
            relator=r.juris.relator,
            classe=r.juris.classe,
            url=r.juris.url,
        )
        if r.juris
        else None,
        stj=StjAcordaoResult(
            id=r.stj.id,
            classe=r.stj.classe,
            relator=r.stj.relator,
            tema=r.stj.tema,
            tese=r.stj.tese,
            ementa=r.stj.ementa,
            data_decisao=r.stj.data_decisao,
            data_publicacao=r.stj.data_publicacao,
        )
        if r.stj
        else None,
        datajud=DatajudCapaResult(
            classe_oficial=r.datajud.classe_oficial,
            assuntos=r.datajud.assuntos,
            orgao_julgador=r.datajud.orgao_julgador,
            grau=r.datajud.grau,
            data_ajuizamento=r.datajud.data_ajuizamento,
            ultima_atualizacao=r.datajud.ultima_atualizacao,
        )
        if r.datajud
        else None,
        documentos=[
            DocumentoResult(
                fonte=d.fonte,
                id_documento=d.id_documento,
                tipo=d.tipo,
                data=d.data,
                url=d.url,
                resumo=d.resumo,
            )
            for d in r.documentos
        ],
        documentos_truncados=r.documentos_truncados,
        dataset_gerado_em=r.dataset_gerado_em,
        consultado_em=datetime.now(UTC).isoformat(timespec="seconds"),
        avisos=r.avisos,
        next_actions=_next_actions(r),
        web_url=_web_url(r.nr_processo_mascara),
        web_path=_web_path(r.nr_processo_mascara),
    )


def _processo_tool_error(exc: Exception) -> ToolError:
    if isinstance(exc, CnjInvalidoError):
        return ToolError(str(exc))
    # duckdb.Error/httpx.HTTPError: indice_processual.parquet em si não pôde
    # ser aberto — não há resposta possível (distinto de uma fonte de
    # origem específica falhar, que service.buscar_processo já absorve como
    # aviso + lacuna vazia, nunca chegando aqui).
    return ToolError(
        "Não foi possível abrir indice_processual.parquet no Internet Archive. "
        "Tente de novo mais tarde; se persistir, o item causaganha-dashboard pode "
        "estar indisponível."
    )


def register(mcp: FastMCP) -> None:
    """Registra ``processo_consultar`` em *mcp*."""

    @mcp.tool(
        name="processo_consultar",
        timeout=_PROCESSO_TOOL_TIMEOUT,
        annotations={
            "title": "Consulta o dossiê unificado de um processo por CNJ",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    def processo_consultar(
        cnj: str,
        incluir_documentos: bool = True,
        limite_documentos: Annotated[
            int, Field(ge=1, le=50, description="Máximo de documentos a retornar.")
        ] = 10,
    ) -> ProcessoConsultarResult:
        """Consulta o dossiê unificado (DJEN + JURIS + STJ + DataJud) de um processo por CNJ.

        Lê os parquets canônicos publicados no Internet Archive (item
        `causaganha-dashboard`) — a mesma fonte que o dashboard web usa para
        `/processo?cnj=...` — sem cache local nesta primeira versão. Retorna
        fatos com proveniência (quais fontes contribuíram, quando o dataset
        foi gerado), nunca um veredito. Um CNJ válido mas ausente de toda
        fonte retorna `encontrado=False`, não é um erro; um CNJ malformado
        (não são 20 dígitos) levanta erro de uso.

        `next_actions` orienta a composição explícita com estado live ou com
        a busca de publicações sem fazer chamadas ocultas a outras fontes.

        Args:
            cnj: Número do processo, com ou sem máscara (aceita ambos).
            incluir_documentos: Se False, pula a busca de documentos
                JURIS/STJ — mais rápido quando só o resumo por fonte importa.
            limite_documentos: Máximo de documentos a retornar, 1-50,
                ordenados do mais recente para o mais antigo.
                `documentos_truncados=True` quando há mais além do limite.
        """
        try:
            resultado = service.buscar_processo(
                cnj,
                incluir_documentos=incluir_documentos,
                limite_documentos=limite_documentos,
            )
        except (CnjInvalidoError, duckdb.Error, httpx.HTTPError) as exc:
            raise _processo_tool_error(exc) from exc
        return _to_result(resultado)
