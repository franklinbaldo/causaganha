"""Execute bounded TEOR searches across published JURIS and STJ datasets."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Any

import duckdb

from causaganha.decisoes.planner import DecisionSearchPlan


@dataclass(frozen=True, slots=True)
class DecisionHit:
    """A normalized piece of decision content with its source preserved."""

    fonte: str
    id_documento: str
    cnj: str | None
    data: str | None
    tipo: str | None
    orgao: str | None
    relator: str | None
    classe: str | None
    trecho: str | None
    url: str | None
    natureza: str = "teor"


@dataclass(slots=True)
class DecisionSearchResult:
    """Results plus enough scope information to qualify empty answers."""

    resultados: list[DecisionHit] = field(default_factory=list)
    resultados_truncados: bool = False
    datasets_consultados: int = 0
    limitacoes: list[str] = field(default_factory=list)


def _url_list_sql(urls: list[str]) -> str:
    escaped = [url.replace("'", "''") for url in urls]
    return ", ".join(f"'{url}'" for url in escaped)


def _load_httpfs(con: duckdb.DuckDBPyConnection) -> None:
    with contextlib.suppress(duckdb.Error):
        con.execute("INSTALL httpfs; LOAD httpfs;")


def _iso(value: Any) -> str | None:  # noqa: ANN401 - DuckDB rows are dynamically typed
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _juris_sql(urls: list[str]) -> str:
    return f"""
        SELECT
            'juris' AS fonte,
            id_documento::VARCHAR AS id_documento,
            NULLIF(regexp_replace(nr_processo, '[^0-9]', '', 'g'), '') AS cnj,
            TRY_CAST(data_julgamento AS DATE) AS data,
            tipo,
            orgao,
            relator,
            classe_judicial AS classe,
            left(texto_limpo, 1200) AS trecho,
            url_portal AS url
        FROM read_parquet([{_url_list_sql(urls)}], union_by_name=true)
        WHERE lower(coalesce(texto_limpo, '')) LIKE lower(?)
          AND (? IS NULL OR TRY_CAST(data_julgamento AS DATE) >= CAST(? AS DATE))
          AND (? IS NULL OR TRY_CAST(data_julgamento AS DATE) <= CAST(? AS DATE))
        ORDER BY data DESC NULLS LAST, id_documento
        LIMIT ?
    """


def _stj_sql(urls: list[str]) -> str:
    return f"""
        SELECT
            'stj' AS fonte,
            id::VARCHAR AS id_documento,
            NULLIF(regexp_replace("numeroProcesso", '[^0-9]', '', 'g'), '') AS cnj,
            TRY_CAST("dataDecisao" AS DATE) AS data,
            "siglaClasse" AS tipo,
            NULL::VARCHAR AS orgao,
            "ministroRelator" AS relator,
            "siglaClasse" AS classe,
            left(coalesce("ementa", "teseJuridica", "tema"), 1200) AS trecho,
            NULL::VARCHAR AS url
        FROM read_parquet([{_url_list_sql(urls)}], union_by_name=true)
        WHERE lower(
            concat_ws(' ', coalesce("ementa", ''), coalesce("teseJuridica", ''), coalesce("tema", ''))
        ) LIKE lower(?)
          AND (? IS NULL OR TRY_CAST("dataDecisao" AS DATE) >= CAST(? AS DATE))
          AND (? IS NULL OR TRY_CAST("dataDecisao" AS DATE) <= CAST(? AS DATE))
        ORDER BY data DESC NULLS LAST, id_documento
        LIMIT ?
    """


def _params(texto: str, plan: DecisionSearchPlan, limite: int) -> list[str | int | None]:
    start = plan.data_inicio.isoformat() if plan.data_inicio else None
    end = plan.data_fim.isoformat() if plan.data_fim else None
    return [f"%{texto}%", start, start, end, end, limite + 1]


def _row_to_hit(row: tuple[Any, ...]) -> DecisionHit:
    fonte, doc_id, cnj, data, tipo, orgao, relator, classe, trecho, url = row
    return DecisionHit(
        fonte=str(fonte),
        id_documento=str(doc_id),
        cnj=str(cnj) if cnj else None,
        data=_iso(data),
        tipo=str(tipo) if tipo else None,
        orgao=str(orgao) if orgao else None,
        relator=str(relator) if relator else None,
        classe=str(classe) if classe else None,
        trecho=str(trecho) if trecho else None,
        url=str(url) if url else None,
    )


def _search_source(
    con: duckdb.DuckDBPyConnection,
    *,
    fonte: str,
    urls: list[str],
    texto: str,
    plan: DecisionSearchPlan,
    limite: int,
) -> tuple[list[DecisionHit], bool, str | None]:
    if not urls:
        return [], False, None
    sql = _juris_sql(urls) if fonte == "juris" else _stj_sql(urls)
    try:
        rows = con.execute(sql, _params(texto, plan, limite)).fetchall()
    except duckdb.Error as exc:
        return [], False, f"Fonte {fonte} indisponível para esta busca: {exc}"
    truncated = len(rows) > limite
    return [_row_to_hit(row) for row in rows[:limite]], truncated, None


def search_decisions(
    texto: str,
    plan: DecisionSearchPlan,
    *,
    limite: int = 20,
) -> DecisionSearchResult:
    """Search decision content without crossing the dataset budget in ``plan``.

    Source failures are isolated: a broken JURIS partition does not erase STJ
    results and vice versa. The caller receives the limitation explicitly.
    """
    query = texto.strip()
    if len(query) < 2:
        msg = "texto deve ter pelo menos 2 caracteres."
        raise ValueError(msg)
    if not 1 <= limite <= 100:
        msg = "limite deve estar entre 1 e 100."
        raise ValueError(msg)

    con = duckdb.connect()
    _load_httpfs(con)
    hits: list[DecisionHit] = []
    limitations: list[str] = []
    truncated = False
    try:
        for fonte, datasets in (("juris", plan.juris), ("stj", plan.stj)):
            source_hits, source_truncated, error = _search_source(
                con,
                fonte=fonte,
                urls=[item.url for item in datasets],
                texto=query,
                plan=plan,
                limite=limite,
            )
            hits.extend(source_hits)
            truncated = truncated or source_truncated
            if error:
                limitations.append(error)
    finally:
        con.close()

    hits.sort(key=lambda item: (item.data or "", item.id_documento), reverse=True)
    if len(hits) > limite:
        hits = hits[:limite]
        truncated = True
    return DecisionSearchResult(
        resultados=hits,
        resultados_truncados=truncated,
        datasets_consultados=plan.total_datasets,
        limitacoes=limitations,
    )
