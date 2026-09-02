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
    discover_published_tcu_dataset,
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
    if fonte in {"todas", "tcu"}:
        tcu_dataset = discover_published_tcu_dataset()
        if tcu_dataset is None:
            limitations.append(
                "TCU: fonte ainda não publicada — nenhum artefato com prova de "
                "leitura verificada está disponível; fonte tcu não é consultada "
                "até essa prova existir."
            )
        else:
            datasets.append(tcu_dataset)
            limitations.append(
                "TCU: cobertura restrita a acórdãos com identidade KEY provada, "
                "publicados entre 2017 e 2026 — anos anteriores não são consultados."
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
        fonte: Literal["todas", "juris", "stj", "tcu"] = "todas",
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
        classe: Annotated[
            str | None,
            Field(
                default=None,
                description="Filtra por classe processual (JURIS `classe_judicial`, "
                "STJ `siglaClasse`). Comparação por substring, sem diferenciar maiúsculas.",
            ),
        ] = None,
        orgao: Annotated[
            str | None,
            Field(
                default=None,
                description="Filtra por órgão julgador. Aplica-se somente a JURIS: o "
                "dataset STJ publicado não expõe órgão colegiado julgador de forma "
                "verificada, então resultados STJ desta busca ignoram esse critério "
                "e a resposta traz uma limitação explícita em vez de fingir o filtro.",
            ),
        ] = None,
        relator: Annotated[
            str | None,
            Field(
                default=None,
                description="Filtra por relator (JURIS `relator`, STJ `ministroRelator`). "
                "Comparação por substring, sem diferenciar maiúsculas.",
            ),
        ] = None,
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

        ``classe`` e ``relator`` filtram JURIS e STJ. ``orgao`` filtra JURIS
        e TCU (mapeado do ``colegiado`` oficial) — mas não STJ: filtrar por
        órgão em STJ exigiria um campo que o dataset publicado hoje não
        expõe de forma verificada, então esse critério nunca é aplicado
        silenciosamente aos resultados STJ: quando usado, ``limitacoes``
        explica que a fonte foi ignorada para esse filtro. TCU não tem
        ``classe`` nem CNJ equivalente, então ``classe``/``cnj`` excluem
        resultados TCU em vez de simular um filtro. Não há filtro de
        assunto: nenhuma fonte tem um campo equivalente legítimo hoje.
        TCU é uma fonte de controle externo federal, não um tribunal
        judicial. Hoje não há artefato TCU publicado com prova de leitura
        verificada, então ``fonte="tcu"`` falha explicitamente em vez de
        devolver zero resultados; quando essa prova existir, a cobertura
        inicial é restrita a acórdãos com identidade KEY provada.
        """
        if not texto and not cnj:
            msg = "Informe texto (mínimo 2 caracteres) ou cnj."
            raise ToolError(msg)
        datasets, coverage_limitations = _datasets_for_source(fonte)
        if fonte == "tcu" and not datasets:
            msg = (
                "Fonte tcu ainda não publicada: nenhum artefato TCU com prova "
                "de leitura verificada está disponível no momento."
            )
            raise ToolError(msg)
        try:
            plan = plan_decision_search(
                datasets,
                fonte=fonte,
                data_inicio=data_inicio,
                data_fim=data_fim,
                consulta_por_cnj=bool(cnj),
            )
            found = search_decisions(
                texto,
                plan,
                limite=limite,
                cnj=cnj,
                offset=offset,
                classe=classe,
                orgao=orgao,
                relator=relator,
            )
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
