"""Execute bounded TEOR searches across published JURIS, STJ and TCU datasets."""

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


def _only_digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


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
        WHERE (? IS NULL OR lower(coalesce(texto_limpo, '')) LIKE lower(?))
          AND (? IS NULL OR NULLIF(regexp_replace(nr_processo, '[^0-9]', '', 'g'), '') = ?)
          AND (? IS NULL OR TRY_CAST(data_julgamento AS DATE) >= CAST(? AS DATE))
          AND (? IS NULL OR TRY_CAST(data_julgamento AS DATE) <= CAST(? AS DATE))
          AND (? IS NULL OR lower(coalesce(classe_judicial, '')) LIKE lower(?))
          AND (? IS NULL OR lower(coalesce(relator, '')) LIKE lower(?))
          AND (? IS NULL OR lower(coalesce(orgao, '')) LIKE lower(?))
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
        WHERE (? IS NULL OR lower(
            concat_ws(' ', coalesce("ementa", ''), coalesce("teseJuridica", ''), coalesce("tema", ''))
        ) LIKE lower(?))
          AND (? IS NULL OR NULLIF(regexp_replace("numeroProcesso", '[^0-9]', '', 'g'), '') = ?)
          AND (? IS NULL OR TRY_CAST("dataDecisao" AS DATE) >= CAST(? AS DATE))
          AND (? IS NULL OR TRY_CAST("dataDecisao" AS DATE) <= CAST(? AS DATE))
          AND (? IS NULL OR lower(coalesce("siglaClasse", '')) LIKE lower(?))
          AND (? IS NULL OR lower(coalesce("ministroRelator", '')) LIKE lower(?))
        ORDER BY data DESC NULLS LAST, id_documento
        LIMIT ?
    """


def _tcu_sql(urls: list[str]) -> str:
    return f"""
        SELECT
            'tcu' AS fonte,
            key::VARCHAR AS id_documento,
            NULL::VARCHAR AS cnj,
            TRY_CAST(data_sessao AS DATE) AS data,
            'Acórdão' AS tipo,
            colegiado AS orgao,
            relator,
            NULL::VARCHAR AS classe,
            left(coalesce(sumario, acordao, decisao, relatorio, voto), 1200) AS trecho,
            NULL::VARCHAR AS url
        FROM read_parquet([{_url_list_sql(urls)}], union_by_name=true)
        WHERE (? IS NULL OR lower(
            concat_ws(
                ' ',
                coalesce(titulo, ''),
                coalesce(assunto, ''),
                coalesce(sumario, ''),
                coalesce(acordao, ''),
                coalesce(decisao, ''),
                coalesce(relatorio, ''),
                coalesce(voto, '')
            )
        ) LIKE lower(?))
          AND (? IS NULL AND ? IS NULL)
          AND (? IS NULL OR TRY_CAST(data_sessao AS DATE) >= CAST(? AS DATE))
          AND (? IS NULL OR TRY_CAST(data_sessao AS DATE) <= CAST(? AS DATE))
          AND (? IS NULL AND ? IS NULL)
          AND (? IS NULL OR lower(coalesce(relator, '')) LIKE lower(?))
          AND (? IS NULL OR lower(coalesce(colegiado, '')) LIKE lower(?))
        ORDER BY data DESC NULLS LAST, id_documento
        LIMIT ?
    """


def _params(
    texto: str | None,
    cnj: str | None,
    plan: DecisionSearchPlan,
    limite: int,
    *,
    classe: str | None,
    relator: str | None,
    orgao: str | None = None,
    include_orgao: bool = False,
) -> list[str | int | None]:
    start = plan.data_inicio.isoformat() if plan.data_inicio else None
    end = plan.data_fim.isoformat() if plan.data_fim else None
    texto_pattern = f"%{texto}%" if texto else None
    cnj_digits = _only_digits(cnj) if cnj else None
    classe_pattern = f"%{classe}%" if classe else None
    relator_pattern = f"%{relator}%" if relator else None
    params: list[str | int | None] = [
        texto_pattern,
        texto_pattern,
        cnj_digits,
        cnj_digits,
        start,
        start,
        end,
        end,
        classe_pattern,
        classe_pattern,
        relator_pattern,
        relator_pattern,
    ]
    if include_orgao:
        orgao_pattern = f"%{orgao}%" if orgao else None
        params.extend([orgao_pattern, orgao_pattern])
    params.append(limite + 1)
    return params


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
    texto: str | None,
    cnj: str | None,
    plan: DecisionSearchPlan,
    limite: int,
    classe: str | None,
    relator: str | None,
    orgao: str | None = None,
) -> tuple[list[DecisionHit], bool, str | None]:
    if not urls:
        return [], False, None
    sql_by_fonte = {"juris": _juris_sql, "stj": _stj_sql, "tcu": _tcu_sql}
    include_orgao = fonte in {"juris", "tcu"}
    sql = sql_by_fonte[fonte](urls)
    params = _params(
        texto,
        cnj,
        plan,
        limite,
        classe=classe,
        relator=relator,
        orgao=orgao,
        include_orgao=include_orgao,
    )
    try:
        rows = con.execute(sql, params).fetchall()
    except duckdb.Error as exc:
        return [], False, f"Fonte {fonte} indisponível para esta busca: {exc}"
    truncated = len(rows) > limite
    return [_row_to_hit(row) for row in rows[:limite]], truncated, None


_MAX_WINDOW = 500


def search_decisions(
    texto: str | None,
    plan: DecisionSearchPlan,
    *,
    limite: int = 20,
    cnj: str | None = None,
    offset: int = 0,
    classe: str | None = None,
    orgao: str | None = None,
    relator: str | None = None,
) -> DecisionSearchResult:
    """Search decision content without crossing the dataset budget in ``plan``.

    ``texto`` and ``cnj`` combine as additional filters when both are given.
    A CNJ-only lookup (``texto=None``) is how a caller with a known process
    number finds teor without guessing a keyword.

    ``classe`` and ``relator`` filter JURIS and STJ, which each have a real,
    comparable column for both. ``orgao`` filters JURIS and TCU (TCU's
    ``colegiado`` is a real, comparable órgão-julgador field) — but not STJ:
    STJ's "órgão colegiado julgador" is not a verified column in the
    published dataset, so honoring it there would risk exactly the kind of
    schema-drift binder error already seen once on this project (see #872).
    Rather than silently ignore the criterion for STJ, ``orgao`` skips STJ
    from the search entirely and records an explicit limitation. TCU has no
    ``classe`` or ``cnj`` equivalent (its process numbers are not CNJs), so a
    ``classe`` or ``cnj`` filter excludes TCU rows rather than fake a match.
    There is no ``assunto`` filter: no source has a legitimate equivalent
    field exposed today.

    ``offset`` pages through the globally sorted, cross-source result set.
    The window (``offset + limite``) is bounded to keep the remote scan cost
    predictable, same spirit as the JURIS date-range budget in ``planner``.

    Source failures are isolated: a broken JURIS partition does not erase STJ
    results and vice versa. The caller receives the limitation explicitly.
    """
    query = (texto or "").strip()
    cnj_digits = _only_digits(cnj) if cnj else ""
    if not query and not cnj_digits:
        msg = "informe texto com pelo menos 2 caracteres, ou informe cnj."
        raise ValueError(msg)
    if query and len(query) < 2:
        msg = "texto deve ter pelo menos 2 caracteres."
        raise ValueError(msg)
    if not 1 <= limite <= 100:
        msg = "limite deve estar entre 1 e 100."
        raise ValueError(msg)
    if offset < 0:
        msg = "offset deve ser maior ou igual a 0."
        raise ValueError(msg)
    window_end = offset + limite
    if window_end > _MAX_WINDOW:
        msg = f"offset + limite não pode exceder {_MAX_WINDOW}."
        raise ValueError(msg)

    texto_query = query or None
    cnj_query = cnj_digits or None
    classe_query = classe.strip() or None if classe else None
    orgao_query = orgao.strip() or None if orgao else None
    relator_query = relator.strip() or None if relator else None
    skip_stj_for_orgao = bool(orgao_query) and bool(plan.stj)

    con = duckdb.connect()
    _load_httpfs(con)
    hits: list[DecisionHit] = []
    limitations: list[str] = []
    truncated = False
    if skip_stj_for_orgao:
        limitations.append(
            "STJ: filtro de órgão não é aplicado — o dataset publicado hoje não "
            "expõe órgão colegiado julgador de forma verificada; resultados STJ "
            "desta busca ignoram esse critério."
        )
    try:
        for fonte, datasets in (("juris", plan.juris), ("stj", plan.stj), ("tcu", plan.tcu)):
            if fonte == "stj" and skip_stj_for_orgao:
                continue
            source_hits, source_truncated, error = _search_source(
                con,
                fonte=fonte,
                urls=[item.url for item in datasets],
                texto=texto_query,
                cnj=cnj_query,
                plan=plan,
                limite=window_end,
                classe=classe_query,
                relator=relator_query,
                orgao=orgao_query,
            )
            hits.extend(source_hits)
            truncated = truncated or source_truncated
            if error:
                limitations.append(error)
    finally:
        con.close()

    hits.sort(key=lambda item: (item.data or "", item.id_documento), reverse=True)
    if len(hits) > window_end:
        truncated = True
    hits = hits[offset:window_end]
    return DecisionSearchResult(
        resultados=hits,
        resultados_truncados=truncated,
        datasets_consultados=plan.total_datasets,
        limitacoes=limitations,
    )
