"""Product-facing TEOR search across published JURIS and STJ decision datasets."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Literal

import httpx
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

from causaganha.decisoes.planner import DecisionSearchBudgetError, plan_decision_search
from causaganha.decisoes.published import (
    PublishedDecisionDataset,
    STJ_PARQUET_URL,
    discover_published_juris_datasets,
)
from causaganha.decisoes.search import search_decisions
from tjro_juris import archive as juris_archive
from tjro_juris.manifest import ManifestFormatError


if TYPE_CHECKING:
    from fastmcp import FastMCP


_SEARCH_TIMEOUT = 45.0


class DecisaoResult(BaseModel):
    """Uma peça de teor normalizada sem apagar sua fonte oficial."""

    fonte: str
    natureza: str = "teor"
    id_documento: str
    cnj: str | None = None
    data: str | None = None
    tipo: str | None = None
    orgao: str | None = None
    relator: str | None = None
    classe: str | None = None
    trecho: str | None = None
    url: str | None = None


class DecisoesBuscarResult(BaseModel):
    """Resultado de uma busca temática bounded em fontes de teor."""

    resumo: str
    resultados: list[DecisaoResult] = Field(default_factory=list)
    resultados_truncados: bool = False
    offset: int = 0
    proximo_offset: int | None = Field(
        default=None,
        description="Offset a informar na próxima chamada para continuar a "
        "paginação; None quando não há mais resultados.",
    )
    datasets_consultados: int = 0
    fonte_solicitada: str
    data_inicio: str | None = None
    data_fim: str | None = None
    natureza: str = "teor"
    consultado_em: str
    limitacoes: list[str] = Field(default_factory=list)
    next_actions: list[dict[str, str]] = Field(default_factory=list)


def _datasets_for_source(fonte: str) -> tuple[list[PublishedDecisionDataset], list[str]]:
    datasets: list[PublishedDecisionDataset] = []
    limitations: list[str] = []
    if fonte in {"todas", "juris"}:
        try:
            manifest_text = juris_archive.read_manifest_text(timeout=10.0)
            if manifest_text is None:
                limitations.append(
                    "Manifest JURIS não publicado; a ausência de resultados não cobre essa fonte."
                )
            else:
                datasets.extend(discover_published_juris_datasets(manifest_text))
        except (httpx.HTTPError, ManifestFormatError) as exc:
            limitations.append(f"Não foi possível verificar a cobertura JURIS: {exc}")
    if fonte in {"todas", "stj"}:
        datasets.append(
            PublishedDecisionDataset(
                fonte="stj",
                url=STJ_PARQUET_URL,
                tipo="acordao",
            )
        )
    return datasets, limitations


def _next_actions(results: list[DecisaoResult]) -> list[dict[str, str]]:
    if any(item.cnj for item in results):
        return [
            {
                "tool": "processo_consultar",
                "quando": "Quando precisar do contexto multi-fonte de um CNJ retornado.",
            },
            {
                "tool": "processo_estado",
                "quando": "Quando precisar do andamento atual de um CNJ retornado.",
            },
        ]
    return []


def register(mcp: FastMCP) -> None:
    """Registra ``decisoes_buscar`` em *mcp*."""

    @mcp.tool(
        name="decisoes_buscar",
        timeout=_SEARCH_TIMEOUT,
        annotations={
            "title": "Busca teor em decisões e acórdãos publicados",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    def decisoes_buscar(
        texto: Annotated[
            str | None,
            Field(
                default=None,
                min_length=2,
                description="Texto livre a localizar no teor/ementa/tese. "
                "Opcional quando ``cnj`` é informado.",
            ),
        ] = None,
        fonte: Literal["todas", "juris", "stj"] = "todas",
        data_inicio: str | None = None,
        data_fim: str | None = None,
        limite: Annotated[int, Field(ge=1, le=50)] = 20,
        cnj: Annotated[
            str | None,
            Field(
                default=None,
                description="CNJ do processo para localizar teor sem exigir "
                "texto/período — dispensa data_inicio/data_fim em JURIS.",
            ),
        ] = None,
        offset: Annotated[
            int,
            Field(
                ge=0,
                description="Deslocamento para continuar a paginação a partir de "
                "um `proximo_offset` retornado anteriormente.",
            ),
        ] = 0,
    ) -> DecisoesBuscarResult:
        """Busca TEOR decisório preservado sem exigir schemas JURIS/STJ do agente.

        Use quando a pergunta depende do que uma decisão, acórdão, ementa ou tese
        efetivamente diz. Para busca temática que inclua TJRO JURIS, informe
        ``data_inicio`` e ``data_fim`` em AAAA-MM-DD; o intervalo é limitado a
        seis meses para impedir scans remotos históricos sem bound. Para pesquisar
        apenas STJ, o período é opcional. Quando o CNJ do processo já é conhecido
        (por exemplo, a partir de ``processo_consultar``), informe ``cnj`` no lugar
        de ``texto`` — a busca por CNJ é um lookup pontual e dispensa
        ``data_inicio``/``data_fim`` mesmo em JURIS.

        Não use para saber o andamento atual de um processo: isso é
        ``processo_estado``. Para um CNJ específico, ``processo_consultar`` é o
        caminho preferido para descobrir documentos já associados ao dossiê.

        Quando ``resultados_truncados`` for True, o resultado traz
        ``proximo_offset``: repita a chamada com ``offset=proximo_offset`` para
        obter a próxima página sem alterar os demais argumentos.
        """
        if not texto and not cnj:
            msg = "Informe texto (mínimo 2 caracteres) ou cnj."
            raise ToolError(msg)
        datasets, coverage_limitations = _datasets_for_source(fonte)
        try:
            plan = plan_decision_search(
                datasets,
                fonte=fonte,
                data_inicio=data_inicio,
                data_fim=data_fim,
                consulta_por_cnj=bool(cnj),
            )
            found = search_decisions(texto, plan, limite=limite, cnj=cnj, offset=offset)
        except (DecisionSearchBudgetError, ValueError) as exc:
            raise ToolError(str(exc)) from exc

        results = [
            DecisaoResult(
                fonte=item.fonte,
                id_documento=item.id_documento,
                cnj=item.cnj,
                data=item.data,
                tipo=item.tipo,
                orgao=item.orgao,
                relator=item.relator,
                classe=item.classe,
                trecho=item.trecho,
                url=item.url,
            )
            for item in found.resultados
        ]
        limitations = [*coverage_limitations, *found.limitacoes]
        summary = (
            f"{len(results)} resultado(s) de teor em {found.datasets_consultados} "
            "dataset(s) publicado(s)."
        )
        return DecisoesBuscarResult(
            resumo=summary,
            resultados=results,
            resultados_truncados=found.resultados_truncados,
            offset=offset,
            proximo_offset=offset + limite if found.resultados_truncados else None,
            datasets_consultados=found.datasets_consultados,
            fonte_solicitada=fonte,
            data_inicio=data_inicio,
            data_fim=data_fim,
            consultado_em=datetime.now(UTC).isoformat(timespec="seconds"),
            limitacoes=limitations,
            next_actions=_next_actions(results),
        )
