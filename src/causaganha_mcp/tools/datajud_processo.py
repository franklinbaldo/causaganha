"""``processo_estado`` — live process state from the official DataJud API.

The tool exposes *estado*, not *teor*: movements prove that events were
registered, but do not reveal the reasoning or content of the underlying
judicial act. For archived publications and decision text, agents should
compose with ``processo_consultar`` instead of inferring content from a
movement label.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Literal

import httpx
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

from datajud import process_service
from datajud.client import (
    API_KEY_ENV,
    DEFAULT_TRIBUNAL,
    WIKI_ACESSO_URL,
    DataJudAuthError,
    DataJudError,
    DataJudProtocolError,
    DataJudRateLimitError,
)
from datajud.models import (
    Movimento,
    ProcessoCapa,
    formatar_cnj,
    normalizar_cnj,
    normalizar_data14,
)


if TYPE_CHECKING:
    from fastmcp import FastMCP


_PROCESSO_TIMEOUT = 15.0
_PROCESSO_MAX_RETRIES = 1
_PROCESSO_BACKOFF_BASE = 1.0
_PROCESSO_TOOL_TIMEOUT = 45.0

# Noise is defined by exclusion, not by trying to enumerate every movement
# that might be legally important. This short list came from real DataJud use
# and is deliberately conservative: unknown/new TPU codes remain visible as
# marcos instead of silently disappearing when the taxonomy evolves.
_RUIDO_MOVIMENTO_CODES = frozenset({1051, 92, 1061, 60, 581})

# Matched against the movement's own name, not a fixed TPU code list: DataJud
# movement taxonomies vary across tribunals/instances, and a name-based match
# stays conservative without trying to enumerate every judgment code by
# court. False positives (a routine movement that happens to contain one of
# these words) only cost an extra next_action suggestion, never a wrong
# conclusion about content — the tool still never reads the ato itself.
_DECISAO_MOVIMENTO_KEYWORDS = (
    "sentença",
    "sentenca",
    "acórdão",
    "acordao",
    "julgamento",
    "decisão",
    "decisao",
)


class DatajudMovimentoResult(BaseModel):
    """One DataJud movement, preserving its source degree and raw timestamp."""

    codigo: int | None = None
    nome: str | None = None
    data_hora: str | None = Field(
        default=None,
        description=(
            "Timestamp returned by DataJud. Ordering uses this raw value before presentation."
        ),
    )
    grau: str = ""
    orgao_julgador: str | None = None
    complementos: str | None = None


class DatajudGrauResult(BaseModel):
    """Metadata for one DataJud record/degree of the process."""

    grau: str = ""
    orgao_julgador: str | None = None
    classe: str | None = None
    assuntos: list[str] = Field(default_factory=list)
    data_ajuizamento: str | None = None
    ultima_atualizacao: str | None = None
    n_movimentos: int = 0


class ProximaAcaoResult(BaseModel):
    """A semantically useful next tool call for an agent."""

    quando: str
    acao: str
    tool: str
    argumentos: dict[str, str | bool | int] = Field(default_factory=dict)


class DatajudProcessoResult(BaseModel):
    """Current DataJud state for one CNJ, summarized for agent use."""

    encontrado: bool
    cnj: str = Field(description="CNJ normalized to 20 digits.")
    cnj_formatado: str
    tribunal: str
    natureza: Literal["estado"] = Field(
        default="estado",
        description=(
            "This tool reports current process-state metadata/movements, not archived content."
        ),
    )
    resumo: str
    graus: list[DatajudGrauResult] = Field(default_factory=list)
    total_movimentos: int = 0
    marcos: list[DatajudMovimentoResult] = Field(
        default_factory=list,
        description="Recent non-noise movements. Noise is removed by a short exclusion list.",
    )
    marcos_truncados: bool = False
    ultimo_marco: DatajudMovimentoResult | None = None
    movimentos: list[DatajudMovimentoResult] = Field(
        default_factory=list,
        description="Raw movement timeline only when incluir_movimentos=True.",
    )
    movimentos_truncados: bool = False
    consultado_em: str
    fonte_oficial: Literal["DataJud/CNJ"] = "DataJud/CNJ"
    limitacoes: list[str] = Field(default_factory=list)
    next_actions: list[ProximaAcaoResult] = Field(default_factory=list)


def _movement_result(capa: ProcessoCapa, mov: Movimento) -> DatajudMovimentoResult:
    complementos = mov.complementos_str()
    return DatajudMovimentoResult(
        codigo=mov.codigo,
        nome=mov.nome,
        data_hora=mov.data_hora,
        grau=capa.grau,
        orgao_julgador=capa.orgao_julgador.nome,
        complementos=complementos or None,
    )


def _is_decisao_movimento(mov: DatajudMovimentoResult) -> bool:
    nome = (mov.nome or "").lower()
    return any(keyword in nome for keyword in _DECISAO_MOVIMENTO_KEYWORDS)


def _movement_sort_key(item: DatajudMovimentoResult) -> str:
    # DataJud timestamps are ISO-like and sort chronologically as raw strings.
    # Most importantly, we never sort a formatted dd/mm/yyyy presentation.
    return item.data_hora or ""


def _grau_result(capa: ProcessoCapa) -> DatajudGrauResult:
    return DatajudGrauResult(
        grau=capa.grau,
        orgao_julgador=capa.orgao_julgador.nome,
        classe=capa.classe.nome,
        assuntos=[a.nome for a in capa.assuntos if a.nome],
        data_ajuizamento=normalizar_data14(capa.data_ajuizamento),
        ultima_atualizacao=capa.data_hora_ultima_atualizacao,
        n_movimentos=len(capa.movimentos),
    )


def _to_result(
    cnj: str,
    tribunal: str,
    capas: list[ProcessoCapa],
    *,
    incluir_movimentos: bool,
    limite_marcos: int,
    limite_movimentos: int,
) -> DatajudProcessoResult:
    normalized = normalizar_cnj(cnj) or cnj
    formatted = formatar_cnj(normalized)
    consulted_at = datetime.now(UTC).isoformat(timespec="seconds")
    tribunal_normalized = tribunal.lower()

    if not capas:
        return DatajudProcessoResult(
            encontrado=False,
            cnj=normalized,
            cnj_formatado=formatted,
            tribunal=tribunal_normalized,
            resumo=(
                f"O DataJud não retornou registro para {formatted} no índice "
                f"{tribunal_normalized.upper()} nesta consulta."
            ),
            consultado_em=consulted_at,
            limitacoes=[
                "Não encontrado neste índice não significa que o processo não existe.",
                (
                    "Confirme se o tribunal consultado corresponde ao processo antes de "
                    "tratar a ausência como evidência."
                ),
            ],
            next_actions=[
                ProximaAcaoResult(
                    quando=(
                        "Se você precisa saber se o CausaGanha já preservou publicações "
                        "ou decisões deste CNJ."
                    ),
                    acao="Consultar o snapshot arquivado multi-fonte.",
                    tool="processo_consultar",
                    argumentos={"cnj": formatted},
                )
            ],
        )

    movimentos_all = [_movement_result(capa, mov) for capa in capas for mov in capa.movimentos]
    movimentos_all.sort(key=_movement_sort_key, reverse=True)
    marcos_all = [m for m in movimentos_all if m.codigo not in _RUIDO_MOVIMENTO_CODES]
    marcos = marcos_all[:limite_marcos]
    ultimo_marco = marcos_all[0] if marcos_all else None

    graus = sorted(
        (_grau_result(capa) for capa in capas),
        key=lambda grau: grau.ultima_atualizacao or "",
        reverse=True,
    )
    movimentos = movimentos_all[:limite_movimentos] if incluir_movimentos else []

    if ultimo_marco and ultimo_marco.nome:
        ultimo = f" Último marco: {ultimo_marco.nome}"
        if ultimo_marco.data_hora:
            ultimo += f" em {ultimo_marco.data_hora}"
        ultimo += "."
    else:
        ultimo = " Nenhum marco não-ruído foi identificado."

    next_actions = [
        ProximaAcaoResult(
            quando=(
                "Se a pergunta exige publicações preservadas, decisão, ementa "
                "ou outro teor documental."
            ),
            acao="Abrir o dossiê arquivado multi-fonte do mesmo CNJ.",
            tool="processo_consultar",
            argumentos={"cnj": formatted},
        )
    ]
    if any(_is_decisao_movimento(m) for m in marcos_all):
        next_actions.append(
            ProximaAcaoResult(
                quando=(
                    "Se a pergunta depende do que a sentença/acórdão/decisão efetivamente "
                    "diz — o movimento acima prova que o ato ocorreu, mas não contém seu "
                    "teor; não infira o conteúdo a partir do nome do movimento."
                ),
                acao="Buscar o teor da decisão correspondente.",
                tool="decisoes_buscar",
                argumentos={"cnj": formatted},
            )
        )
    if not incluir_movimentos and movimentos_all:
        next_actions.append(
            ProximaAcaoResult(
                quando=(
                    "Se você precisa inspecionar também movimentos de rotina que foram "
                    "omitidos do resumo."
                ),
                acao="Repetir a consulta incluindo a linha completa de movimentos.",
                tool="processo_estado",
                argumentos={
                    "cnj": formatted,
                    "tribunal": tribunal_normalized,
                    "incluir_movimentos": True,
                },
            )
        )

    return DatajudProcessoResult(
        encontrado=True,
        cnj=normalized,
        cnj_formatado=formatted,
        tribunal=tribunal_normalized,
        resumo=(
            f"DataJud retornou {len(capas)} registro(s)/grau(s) e "
            f"{len(movimentos_all)} movimento(s) para {formatted}." + ultimo
        ),
        graus=graus,
        total_movimentos=len(movimentos_all),
        marcos=marcos,
        marcos_truncados=len(marcos_all) > limite_marcos,
        ultimo_marco=ultimo_marco,
        movimentos=movimentos,
        movimentos_truncados=incluir_movimentos and len(movimentos_all) > limite_movimentos,
        consultado_em=consulted_at,
        limitacoes=[
            (
                "DataJud informa metadados e movimentos; um movimento de sentença/decisão "
                "não contém, por si só, a fundamentação ou o teor do ato."
            ),
            (
                "A consulta é ao índice oficial do tribunal indicado e reflete o que o "
                "DataJud retornou no instante consultado."
            ),
        ],
        next_actions=next_actions,
    )


def _tool_error(exc: Exception) -> ToolError:
    if isinstance(exc, DataJudAuthError):
        return ToolError(
            "O DataJud rejeitou a chave de API configurada (HTTP 401). É um problema de "
            f"credencial do operador; consulte {WIKI_ACESSO_URL} e configure {API_KEY_ENV}."
        )
    if isinstance(exc, DataJudRateLimitError):
        return ToolError(
            "O DataJud limitou a consulta além do orçamento interativo de retry. "
            "Tente novamente mais tarde."
        )
    if isinstance(exc, DataJudProtocolError):
        return ToolError(f"O DataJud retornou uma resposta não interpretável: {exc}")
    if isinstance(exc, httpx.TimeoutException | httpx.TransportError):
        return ToolError(
            "Erro de rede ao consultar o processo no DataJud. Tente novamente; "
            "se persistir, a API oficial pode estar indisponível."
        )
    if isinstance(exc, httpx.HTTPStatusError):
        return ToolError(f"O DataJud retornou HTTP {exc.response.status_code} para esta consulta.")
    return ToolError(
        "O DataJud não conseguiu concluir a consulta do processo. Tente novamente mais tarde."
    )


def register(mcp: FastMCP) -> None:
    """Register the live process-state tool."""

    @mcp.tool(
        name="processo_estado",
        timeout=_PROCESSO_TOOL_TIMEOUT,
        annotations={
            "title": "Consulta o estado atual de um processo no DataJud",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def processo_estado(
        cnj: str,
        tribunal: str = DEFAULT_TRIBUNAL,
        *,
        incluir_movimentos: bool = False,
        limite_marcos: Annotated[
            int, Field(ge=1, le=100, description="Máximo de marcos não-ruído a retornar.")
        ] = 25,
        limite_movimentos: Annotated[
            int, Field(ge=1, le=500, description="Máximo de movimentos brutos quando solicitados.")
        ] = 200,
    ) -> DatajudProcessoResult:
        """Consulta ao vivo metadados e movimentos de um CNJ no DataJud oficial.

        Use quando a pergunta for sobre **estado processual**: último andamento,
        trajetória, graus ou movimentos registrados. Não use esta tool para
        responder o que uma sentença/decisão *diz*: DataJud registra o evento,
        não necessariamente o teor. Para arquivo, publicações e documentos,
        componha com `processo_consultar`.

        Por padrão retorna um resumo econômico: graus, contagem, marcos
        recentes e último marco entre todos os graus. Movimentos de rotina são
        filtrados dos `marcos` por uma lista curta de exclusão; códigos novos ou
        desconhecidos permanecem visíveis. A linha bruta completa só é
        retornada quando `incluir_movimentos=True`.
        """
        normalized = normalizar_cnj(cnj)
        if not normalized:
            msg = "CNJ inválido: informe os 20 dígitos do número do processo, com ou sem máscara."
            raise ToolError(msg)

        try:
            capas = await process_service.consultar_processo(
                normalized,
                tribunal,
                request_timeout=_PROCESSO_TIMEOUT,
                max_retries=_PROCESSO_MAX_RETRIES,
                backoff_base=_PROCESSO_BACKOFF_BASE,
            )
        except (DataJudError, httpx.HTTPError) as exc:
            raise _tool_error(exc) from exc

        return _to_result(
            normalized,
            tribunal,
            capas,
            incluir_movimentos=incluir_movimentos,
            limite_marcos=limite_marcos,
            limite_movimentos=limite_movimentos,
        )
