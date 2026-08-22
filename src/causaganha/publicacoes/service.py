"""Busca semântica nos Parquets DJEN canônicos publicados no Internet Archive.

O serviço esconde do consumidor o catálogo físico, nomes de tabelas e joins.
A fonte normal é o arquivo público do CausaGanha: ``manifest.parquet`` serve
como índice dos Parquets remotos e DuckDB/httpfs lê apenas o escopo necessário.
A API live do DJEN não participa desta consulta e nunca é fallback silencioso.
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import duckdb

from causaganha.processos.cnj import formatar_cnj, normalizar_cnj
from causaganha.publicacoes.models import (
    AcervoIndisponivelError,
    CatalogoIndisponivelError,
    CoberturaArquivo,
    CriteriosInvalidosError,
    PublicacaoArquivo,
    PublicacoesBusca,
    PublicacoesQuery,
)


IA_CATALOG_BASE = "https://archive.org/download/causaganha-catalog"
MANIFEST_URL = f"{IA_CATALOG_BASE}/manifest.parquet"
BACKFILL_URL = f"{IA_CATALOG_BASE}/backfill-needed.parquet"

_ITEM_YEAR_RE = re.compile(r"-(20\d{2})$")
_MAX_LIMIT = 50
_MAX_PAGE = 1000
_YEAR_PREFIX_LEN = 4


@dataclass(frozen=True)
class _ManifestEntry:
    tribunal: str
    table_name: str
    ia_item: str
    ia_url: str
    date_value: str | None

    @property
    def year(self) -> int | None:
        match = _ITEM_YEAR_RE.search(self.ia_item)
        if match:
            return int(match.group(1))
        if (
            self.date_value
            and len(self.date_value) >= _YEAR_PREFIX_LEN
            and self.date_value[:_YEAR_PREFIX_LEN].isdigit()
        ):
            return int(self.date_value[:_YEAR_PREFIX_LEN])
        return None


@dataclass(frozen=True)
class _ValidatedQuery:
    query: PublicacoesQuery
    start: date | None
    end: date | None


def _sql_literal(value: str) -> str:
    """Quote an internally selected path/URL for a DuckDB table function."""
    return "'" + value.replace("'", "''") + "'"


def _read_parquet_sql(urls: list[str]) -> str:
    quoted = ", ".join(_sql_literal(url) for url in urls)
    return f"read_parquet([{quoted}], union_by_name=true)"


def _is_remote(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def _load_httpfs(con: duckdb.DuckDBPyConnection, *values: str) -> None:
    if not any(_is_remote(value) for value in values):
        return
    with contextlib.suppress(duckdb.Error):
        con.execute("INSTALL httpfs; LOAD httpfs;")


def _parse_date(value: str | None, field_name: str) -> date | None:
    if value is None or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        msg = f"{field_name} inválida: use AAAA-MM-DD."
        raise CriteriosInvalidosError(msg) from exc


def _normalize_oab(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"[^A-Za-z0-9]", "", value).upper()
    return normalized or None


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_query(query: PublicacoesQuery) -> PublicacoesQuery:
    processo = _normalize_optional(query.processo)
    if processo:
        processo = normalizar_cnj(processo)
        if not processo:
            msg = "CNJ inválido: informe os 20 dígitos, com ou sem máscara."
            raise CriteriosInvalidosError(msg)

    return PublicacoesQuery(
        processo=processo,
        oab=_normalize_oab(query.oab),
        uf_oab=(_normalize_optional(query.uf_oab) or "").upper() or None,
        parte=_normalize_optional(query.parte),
        advogado=_normalize_optional(query.advogado),
        texto=_normalize_optional(query.texto),
        tribunal=(_normalize_optional(query.tribunal) or "").upper() or None,
        data_inicio=_normalize_optional(query.data_inicio),
        data_fim=_normalize_optional(query.data_fim),
        incluir_trecho=query.incluir_trecho,
        limite=query.limite,
        pagina=query.pagina,
    )


def _validate_query(query: PublicacoesQuery) -> _ValidatedQuery:
    normalized = _normalize_query(query)
    semantic_values = (
        normalized.processo,
        normalized.oab,
        normalized.uf_oab,
        normalized.parte,
        normalized.advogado,
        normalized.texto,
        normalized.tribunal,
        normalized.data_inicio,
        normalized.data_fim,
    )
    if not any(semantic_values):
        msg = (
            "Informe ao menos um critério: processo, OAB, parte, advogado, "
            "texto, tribunal ou período."
        )
        raise CriteriosInvalidosError(msg)
    if not 1 <= normalized.limite <= _MAX_LIMIT:
        msg = f"limite deve estar entre 1 e {_MAX_LIMIT}."
        raise CriteriosInvalidosError(msg)
    if not 1 <= normalized.pagina <= _MAX_PAGE:
        msg = f"pagina deve estar entre 1 e {_MAX_PAGE}."
        raise CriteriosInvalidosError(msg)

    start = _parse_date(normalized.data_inicio, "data_inicio")
    end = _parse_date(normalized.data_fim, "data_fim")
    if start and end and start > end:
        msg = "data_inicio não pode ser posterior a data_fim."
        raise CriteriosInvalidosError(msg)
    return _ValidatedQuery(query=normalized, start=start, end=end)


def _load_manifest(con: duckdb.DuckDBPyConnection, manifest_url: str) -> list[_ManifestEntry]:
    _load_httpfs(con, manifest_url)
    source = _sql_literal(manifest_url)
    try:
        rows = con.execute(
            f"""
            SELECT tribunal, table_name, ia_item, ia_url, CAST(date AS VARCHAR)
            FROM read_parquet({source})
            WHERE file_type = 'parquet' AND table_name IS NOT NULL
            """
        ).fetchall()
    except duckdb.Error as exc:
        msg = "Não foi possível abrir o catálogo público de Parquets do CausaGanha."
        raise CatalogoIndisponivelError(msg) from exc

    return [
        _ManifestEntry(
            tribunal=str(tribunal or "").upper(),
            table_name=str(table_name or ""),
            ia_item=str(ia_item or ""),
            ia_url=str(ia_url or ""),
            date_value=str(date_value) if date_value else None,
        )
        for tribunal, table_name, ia_item, ia_url, date_value in rows
        if ia_url
    ]


def _scope_manifest(
    entries: list[_ManifestEntry],
    *,
    tribunal: str | None,
    start: date | None,
    end: date | None,
) -> list[_ManifestEntry]:
    min_year = start.year if start else None
    max_year = end.year if end else None
    scoped: list[_ManifestEntry] = []
    for entry in entries:
        if tribunal and entry.tribunal != tribunal:
            continue
        if min_year is not None or max_year is not None:
            year = entry.year
            if year is None:
                continue
            if min_year is not None and year < min_year:
                continue
            if max_year is not None and year > max_year:
                continue
        scoped.append(entry)
    return scoped


def _urls_by_table(entries: list[_ManifestEntry]) -> dict[str, list[str]]:
    grouped: dict[str, set[str]] = {}
    for entry in entries:
        grouped.setdefault(entry.table_name, set()).add(entry.ia_url)
    return {name: sorted(urls) for name, urls in grouped.items()}


def _required_tables(query: PublicacoesQuery) -> set[str]:
    required = {"comunicacoes"}
    if query.oab or query.uf_oab or query.advogado:
        required.update({"advogados", "comunicacao_advogados"})
    if query.parte:
        required.add("destinatarios")
    if query.texto:
        required.add("textos")
    return required


def _missing_tables(urls: dict[str, list[str]], query: PublicacoesQuery) -> list[str]:
    required = _required_tables(query)
    return sorted(table for table in required if not urls.get(table))


def _build_relations(
    urls: dict[str, list[str]], query: PublicacoesQuery
) -> tuple[list[str], list[str], bool]:
    ctes = [f"comunicacoes AS (SELECT * FROM {_read_parquet_sql(urls['comunicacoes'])})"]
    joins: list[str] = []

    if query.oab or query.uf_oab or query.advogado:
        ctes.extend(
            [
                f"advogados AS (SELECT * FROM {_read_parquet_sql(urls['advogados'])})",
                (
                    "comunicacao_advogados AS (SELECT * FROM "
                    f"{_read_parquet_sql(urls['comunicacao_advogados'])})"
                ),
            ]
        )
        joins.extend(
            [
                "JOIN comunicacao_advogados ca "
                "ON ca.comunicacao_id = c.id AND ca.tribunal = c.tribunal",
                "JOIN advogados a ON a.id = ca.advogado_id AND a.tribunal = c.tribunal",
            ]
        )
    if query.parte:
        ctes.append(
            f"destinatarios AS (SELECT * FROM {_read_parquet_sql(urls['destinatarios'])})"
        )
        joins.append(
            "JOIN destinatarios d ON d.comunicacao_id = c.id AND d.tribunal = c.tribunal"
        )

    use_texts = bool(query.texto or (query.incluir_trecho and urls.get("textos")))
    if use_texts:
        ctes.append(f"textos AS (SELECT * FROM {_read_parquet_sql(urls['textos'])})")
        joins.append("LEFT JOIN textos t ON t.id = c.texto_id")
    return ctes, joins, use_texts


def _build_filters(
    query: PublicacoesQuery, start: date | None, end: date | None
) -> tuple[list[str], list[Any]]:
    where: list[str] = []
    params: list[Any] = []
    if query.processo:
        where.append(
            "regexp_replace(CAST(c.numero_processo AS VARCHAR), '[^0-9]', '', 'g') = ?"
        )
        params.append(query.processo)
    if query.oab:
        where.append(
            "regexp_replace(upper(COALESCE(a.numero_oab, '')), '[^A-Z0-9]', '', 'g') = ?"
        )
        params.append(query.oab)
    if query.uf_oab:
        where.append("upper(COALESCE(a.uf_oab, '')) = ?")
        params.append(query.uf_oab)
    if query.advogado:
        where.append("COALESCE(a.nome, '') ILIKE '%' || ? || '%'")
        params.append(query.advogado)
    if query.parte:
        where.append("COALESCE(d.nome, '') ILIKE '%' || ? || '%'")
        params.append(query.parte)
    if query.texto:
        where.append("COALESCE(t.texto, '') ILIKE '%' || ? || '%'")
        params.append(query.texto)
    if query.tribunal:
        where.append("upper(COALESCE(c.tribunal, '')) = ?")
        params.append(query.tribunal)
    if start:
        where.append("c.data_disponibilizacao >= ?")
        params.append(start.isoformat())
    if end:
        where.append("c.data_disponibilizacao <= ?")
        params.append(end.isoformat())
    return where, params


def _query_parts(
    urls: dict[str, list[str]], validated: _ValidatedQuery
) -> tuple[str, list[Any], list[str]]:
    missing = _missing_tables(urls, validated.query)
    if missing:
        return "", [], missing

    ctes, joins, use_texts = _build_relations(urls, validated.query)
    where, params = _build_filters(validated.query, validated.start, validated.end)
    trecho_expr = (
        "left(regexp_replace(COALESCE(t.texto, ''), '<[^>]+>', ' ', 'g'), 500)"
        if use_texts
        else "NULL::VARCHAR"
    )
    where_sql = " AND ".join(where) if where else "TRUE"
    sql = f"""
        WITH {", ".join(ctes)},
        encontrados AS (
            SELECT DISTINCT
                CAST(c.id AS VARCHAR) AS id,
                c.data_disponibilizacao,
                c.tribunal,
                c.tipo_comunicacao,
                c.nome_orgao,
                CAST(c.numero_processo AS VARCHAR) AS numero_processo,
                c.numero_processo_mascara,
                c.link,
                c.tipo_documento,
                c.nome_classe,
                {trecho_expr} AS trecho,
                c.p_item_ia
            FROM comunicacoes c
            {' '.join(joins)}
            WHERE {where_sql}
        )
        SELECT *, COUNT(*) OVER()::BIGINT AS total_encontrado
        FROM encontrados
        ORDER BY data_disponibilizacao DESC NULLS LAST, id
        LIMIT ? OFFSET ?
    """
    return sql, params, []


def _coverage(
    con: duckdb.DuckDBPyConnection,
    *,
    backfill_url: str,
    tribunal: str | None,
    start: date | None,
    end: date | None,
    arquivos_consultados: int,
    itens_consultados: int,
) -> CoberturaArquivo:
    _load_httpfs(con, backfill_url)
    clauses: list[str] = []
    params: list[str] = []
    if tribunal:
        clauses.append("upper(tribunal) = ?")
        params.append(tribunal)
    if start:
        clauses.append("date >= ?")
        params.append(start.isoformat())
    if end:
        clauses.append("date <= ?")
        params.append(end.isoformat())
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        row = con.execute(
            f"SELECT COUNT(*)::BIGINT FROM read_parquet({_sql_literal(backfill_url)}) {where_sql}",
            params,
        ).fetchone()
    except duckdb.Error:
        return CoberturaArquivo(
            status="desconhecida",
            lacunas_conhecidas=None,
            arquivos_consultados=arquivos_consultados,
            itens_consultados=itens_consultados,
            aviso=(
                "O índice de lacunas conhecidas não pôde ser consultado; zero resultados não deve "
                "ser interpretado como prova de ausência de publicação."
            ),
        )

    gaps = int(row[0]) if row else 0
    if gaps:
        return CoberturaArquivo(
            status="parcial",
            lacunas_conhecidas=gaps,
            arquivos_consultados=arquivos_consultados,
            itens_consultados=itens_consultados,
            aviso=(
                f"Há {gaps} lacuna(s) conhecida(s) de coleta no escopo. A ausência de resultado "
                "é evidência incompleta."
            ),
        )
    return CoberturaArquivo(
        status="sem_lacuna_conhecida",
        lacunas_conhecidas=0,
        arquivos_consultados=arquivos_consultados,
        itens_consultados=itens_consultados,
        aviso=(
            "O catálogo não registra lacuna conhecida no escopo; isso qualifica a cobertura, "
            "mas não transforma o arquivo em uma consulta live ao DJEN."
        ),
    )


def _to_publicacao(row: tuple[Any, ...]) -> PublicacaoArquivo:
    (
        id_,
        data_value,
        tribunal,
        tipo,
        orgao,
        numero_processo,
        numero_mascara,
        link,
        tipo_documento,
        classe,
        trecho,
        ia_item,
        _total,
    ) = row
    raw_cnj = str(numero_processo) if numero_processo else None
    cnj = normalizar_cnj(raw_cnj) if raw_cnj else None
    mascara = formatar_cnj(cnj) if cnj else (str(numero_mascara) if numero_mascara else None)
    return PublicacaoArquivo(
        id=str(id_),
        data=(
            data_value.isoformat()
            if hasattr(data_value, "isoformat")
            else str(data_value or "") or None
        ),
        tribunal=str(tribunal) if tribunal else None,
        tipo=str(tipo) if tipo else None,
        orgao=str(orgao) if orgao else None,
        numero_processo=cnj or raw_cnj,
        numero_processo_mascara=mascara,
        link=str(link) if link else None,
        tipo_documento=str(tipo_documento) if tipo_documento else None,
        classe=str(classe) if classe else None,
        trecho=str(trecho).strip() if trecho else None,
        ia_item=str(ia_item) if ia_item else None,
    )


def _criteria_dict(validated: _ValidatedQuery) -> dict[str, str | bool | int | None]:
    query = validated.query
    return {
        "processo": query.processo,
        "oab": query.oab,
        "uf_oab": query.uf_oab,
        "parte": query.parte,
        "advogado": query.advogado,
        "texto": query.texto,
        "tribunal": query.tribunal,
        "data_inicio": validated.start.isoformat() if validated.start else None,
        "data_fim": validated.end.isoformat() if validated.end else None,
        "incluir_trecho": query.incluir_trecho,
    }


def _insufficient_result(
    validated: _ValidatedQuery,
    missing: list[str],
    *,
    arquivos: int,
    itens: int,
) -> PublicacoesBusca:
    aviso = (
        "O catálogo não contém todos os Parquets necessários para estes critérios "
        f"no escopo selecionado: {', '.join(missing)}."
    )
    cobertura = CoberturaArquivo(
        status="insuficiente",
        lacunas_conhecidas=None,
        arquivos_consultados=arquivos,
        itens_consultados=itens,
        aviso=aviso,
    )
    return PublicacoesBusca(
        resultados=[],
        total_encontrado=0,
        pagina=validated.query.pagina,
        limite=validated.query.limite,
        resultados_truncados=False,
        cobertura=cobertura,
        criterios=_criteria_dict(validated),
        consultado_em=datetime.now(UTC).isoformat(timespec="seconds"),
        avisos=[aviso],
    )


def buscar_publicacoes(
    query: PublicacoesQuery,
    *,
    manifest_url: str = MANIFEST_URL,
    backfill_url: str = BACKFILL_URL,
) -> PublicacoesBusca:
    """Busca publicações no arquivo canônico sem expor schema físico ao chamador."""
    validated = _validate_query(query)
    con = duckdb.connect()
    try:
        manifest = _load_manifest(con, manifest_url)
        scoped = _scope_manifest(
            manifest,
            tribunal=validated.query.tribunal,
            start=validated.start,
            end=validated.end,
        )
        urls = _urls_by_table(scoped)
        query_sql, params, missing = _query_parts(urls, validated)
        communication_entries = [entry for entry in scoped if entry.table_name == "comunicacoes"]
        itens = {entry.ia_item for entry in communication_entries}
        arquivos = len(communication_entries)

        if missing:
            return _insufficient_result(
                validated,
                missing,
                arquivos=arquivos,
                itens=len(itens),
            )

        selected_urls = sorted({url for values in urls.values() for url in values})
        _load_httpfs(con, manifest_url, backfill_url, *selected_urls)
        offset = (validated.query.pagina - 1) * validated.query.limite
        try:
            rows = con.execute(
                query_sql,
                [*params, validated.query.limite, offset],
            ).fetchall()
        except duckdb.Error as exc:
            msg = "Não foi possível consultar os Parquets necessários no arquivo público."
            raise AcervoIndisponivelError(msg) from exc

        total = int(rows[0][-1]) if rows else 0
        resultados = [_to_publicacao(row) for row in rows]
        cobertura = _coverage(
            con,
            backfill_url=backfill_url,
            tribunal=validated.query.tribunal,
            start=validated.start,
            end=validated.end,
            arquivos_consultados=arquivos,
            itens_consultados=len(itens),
        )
        avisos = [cobertura.aviso] if cobertura.aviso else []
        return PublicacoesBusca(
            resultados=resultados,
            total_encontrado=total,
            pagina=validated.query.pagina,
            limite=validated.query.limite,
            resultados_truncados=offset + len(resultados) < total,
            cobertura=cobertura,
            criterios=_criteria_dict(validated),
            consultado_em=datetime.now(UTC).isoformat(timespec="seconds"),
            avisos=avisos,
        )
    finally:
        con.close()
