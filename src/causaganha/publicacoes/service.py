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
)


IA_CATALOG_BASE = "https://archive.org/download/causaganha-catalog"
MANIFEST_URL = f"{IA_CATALOG_BASE}/manifest.parquet"
BACKFILL_URL = f"{IA_CATALOG_BASE}/backfill-needed.parquet"

_ITEM_YEAR_RE = re.compile(r"-(20\d{2})$")
_MAX_LIMIT = 50
_MAX_PAGE = 1000


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
        if self.date_value and len(self.date_value) >= 4 and self.date_value[:4].isdigit():
            return int(self.date_value[:4])
        return None


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


def _validate_query(
    *,
    processo: str | None,
    oab: str | None,
    uf_oab: str | None,
    parte: str | None,
    advogado: str | None,
    texto: str | None,
    tribunal: str | None,
    data_inicio: str | None,
    data_fim: str | None,
    limite: int,
    pagina: int,
) -> tuple[dict[str, str | None], date | None, date | None]:
    values = {
        "processo": _normalize_optional(processo),
        "oab": _normalize_oab(oab),
        "uf_oab": _normalize_optional(uf_oab),
        "parte": _normalize_optional(parte),
        "advogado": _normalize_optional(advogado),
        "texto": _normalize_optional(texto),
        "tribunal": _normalize_optional(tribunal),
    }
    if not any(values.values()) and not data_inicio and not data_fim:
        raise CriteriosInvalidosError(
            "Informe ao menos um critério: processo, OAB, parte, advogado, texto, tribunal ou período."
        )
    if values["processo"]:
        normalized = normalizar_cnj(values["processo"])
        if not normalized:
            raise CriteriosInvalidosError(
                "CNJ inválido: informe os 20 dígitos, com ou sem máscara."
            )
        values["processo"] = normalized
    if values["uf_oab"]:
        values["uf_oab"] = values["uf_oab"].upper()
    if values["tribunal"]:
        values["tribunal"] = values["tribunal"].upper()
    if not 1 <= limite <= _MAX_LIMIT:
        raise CriteriosInvalidosError(f"limite deve estar entre 1 e {_MAX_LIMIT}.")
    if not 1 <= pagina <= _MAX_PAGE:
        raise CriteriosInvalidosError(f"pagina deve estar entre 1 e {_MAX_PAGE}.")

    start = _parse_date(data_inicio, "data_inicio")
    end = _parse_date(data_fim, "data_fim")
    if start and end and start > end:
        raise CriteriosInvalidosError("data_inicio não pode ser posterior a data_fim.")
    return values, start, end


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
        raise CatalogoIndisponivelError(
            "Não foi possível abrir o catálogo público de Parquets do CausaGanha."
        ) from exc

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


def _query_parts(
    urls: dict[str, list[str]],
    criteria: dict[str, str | None],
    *,
    start: date | None,
    end: date | None,
    incluir_trecho: bool,
) -> tuple[str, list[Any], list[str]]:
    """Build the internal query and its bind parameters.

    Only manifest-selected URLs are interpolated. Every user-provided value is
    a bind parameter; the MCP never exposes arbitrary SQL, table names or URLs.
    """
    missing: list[str] = []
    if not urls.get("comunicacoes"):
        missing.append("comunicacoes")
    needs_advogados = bool(criteria["oab"] or criteria["uf_oab"] or criteria["advogado"])
    needs_partes = bool(criteria["parte"])
    needs_textos = bool(criteria["texto"])
    if needs_advogados:
        for table in ("advogados", "comunicacao_advogados"):
            if not urls.get(table):
                missing.append(table)
    if needs_partes and not urls.get("destinatarios"):
        missing.append("destinatarios")
    if needs_textos and not urls.get("textos"):
        missing.append("textos")
    if missing:
        return "", [], sorted(set(missing))

    ctes = [f"comunicacoes AS (SELECT * FROM {_read_parquet_sql(urls['comunicacoes'])})"]
    joins: list[str] = []
    where: list[str] = []
    params: list[Any] = []

    if needs_advogados:
        ctes.append(f"advogados AS (SELECT * FROM {_read_parquet_sql(urls['advogados'])})")
        ctes.append(
            "comunicacao_advogados AS "
            f"(SELECT * FROM {_read_parquet_sql(urls['comunicacao_advogados'])})"
        )
        joins.extend(
            [
                "JOIN comunicacao_advogados ca "
                "ON ca.comunicacao_id = c.id AND ca.tribunal = c.tribunal",
                "JOIN advogados a ON a.id = ca.advogado_id AND a.tribunal = c.tribunal",
            ]
        )
    if needs_partes:
        ctes.append(f"destinatarios AS (SELECT * FROM {_read_parquet_sql(urls['destinatarios'])})")
        joins.append("JOIN destinatarios d ON d.comunicacao_id = c.id AND d.tribunal = c.tribunal")

    use_texts = needs_textos or (incluir_trecho and bool(urls.get("textos")))
    if use_texts:
        ctes.append(f"textos AS (SELECT * FROM {_read_parquet_sql(urls['textos'])})")
        joins.append("LEFT JOIN textos t ON t.id = c.texto_id")

    if criteria["processo"]:
        where.append("regexp_replace(CAST(c.numero_processo AS VARCHAR), '[^0-9]', '', 'g') = ?")
        params.append(criteria["processo"])
    if criteria["oab"]:
        where.append("regexp_replace(upper(COALESCE(a.numero_oab, '')), '[^A-Z0-9]', '', 'g') = ?")
        params.append(criteria["oab"])
    if criteria["uf_oab"]:
        where.append("upper(COALESCE(a.uf_oab, '')) = ?")
        params.append(criteria["uf_oab"])
    if criteria["advogado"]:
        where.append("COALESCE(a.nome, '') ILIKE '%' || ? || '%'")
        params.append(criteria["advogado"])
    if criteria["parte"]:
        where.append("COALESCE(d.nome, '') ILIKE '%' || ? || '%'")
        params.append(criteria["parte"])
    if criteria["texto"]:
        where.append("COALESCE(t.texto, '') ILIKE '%' || ? || '%'")
        params.append(criteria["texto"])
    if criteria["tribunal"]:
        where.append("upper(COALESCE(c.tribunal, '')) = ?")
        params.append(criteria["tribunal"])
    if start:
        where.append("c.data_disponibilizacao >= ?")
        params.append(start.isoformat())
    if end:
        where.append("c.data_disponibilizacao <= ?")
        params.append(end.isoformat())

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
            {" ".join(joins)}
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
        data=data_value.isoformat()
        if hasattr(data_value, "isoformat")
        else str(data_value or "") or None,
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


def buscar_publicacoes(
    *,
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
    limite: int = 10,
    pagina: int = 1,
    manifest_url: str = MANIFEST_URL,
    backfill_url: str = BACKFILL_URL,
) -> PublicacoesBusca:
    """Busca publicações no arquivo canônico, sem expor o schema físico ao chamador."""
    criteria, start, end = _validate_query(
        processo=processo,
        oab=oab,
        uf_oab=uf_oab,
        parte=parte,
        advogado=advogado,
        texto=texto,
        tribunal=tribunal,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limite=limite,
        pagina=pagina,
    )
    con = duckdb.connect()
    try:
        manifest = _load_manifest(con, manifest_url)
        scoped = _scope_manifest(
            manifest,
            tribunal=criteria["tribunal"],
            start=start,
            end=end,
        )
        urls = _urls_by_table(scoped)
        query_sql, params, missing = _query_parts(
            urls,
            criteria,
            start=start,
            end=end,
            incluir_trecho=incluir_trecho,
        )
        communication_entries = [entry for entry in scoped if entry.table_name == "comunicacoes"]
        itens = {entry.ia_item for entry in communication_entries}
        arquivos = len(communication_entries)

        if missing:
            cobertura = CoberturaArquivo(
                status="insuficiente",
                lacunas_conhecidas=None,
                arquivos_consultados=arquivos,
                itens_consultados=len(itens),
                aviso=(
                    "O catálogo não contém todos os Parquets necessários para estes critérios "
                    f"no escopo selecionado: {', '.join(missing)}."
                ),
            )
            return PublicacoesBusca(
                resultados=[],
                total_encontrado=0,
                pagina=pagina,
                limite=limite,
                resultados_truncados=False,
                cobertura=cobertura,
                criterios={
                    **criteria,
                    "data_inicio": start.isoformat() if start else None,
                    "data_fim": end.isoformat() if end else None,
                    "incluir_trecho": incluir_trecho,
                },
                consultado_em=datetime.now(UTC).isoformat(timespec="seconds"),
                avisos=[cobertura.aviso] if cobertura.aviso else [],
            )

        selected_urls = sorted({url for values in urls.values() for url in values})
        _load_httpfs(con, manifest_url, backfill_url, *selected_urls)
        offset = (pagina - 1) * limite
        try:
            rows = con.execute(query_sql, [*params, limite, offset]).fetchall()
        except duckdb.Error as exc:
            raise AcervoIndisponivelError(
                "Não foi possível consultar os Parquets necessários no arquivo público."
            ) from exc

        total = int(rows[0][-1]) if rows else 0
        resultados = [_to_publicacao(row) for row in rows]
        cobertura = _coverage(
            con,
            backfill_url=backfill_url,
            tribunal=criteria["tribunal"],
            start=start,
            end=end,
            arquivos_consultados=arquivos,
            itens_consultados=len(itens),
        )
        avisos = [cobertura.aviso] if cobertura.aviso else []
        if incluir_trecho and not urls.get("textos"):
            avisos.append(
                "Trechos não puderam ser carregados porque textos.parquet não existe neste escopo."
            )
        return PublicacoesBusca(
            resultados=resultados,
            total_encontrado=total,
            pagina=pagina,
            limite=limite,
            resultados_truncados=offset + len(resultados) < total,
            cobertura=cobertura,
            criterios={
                **criteria,
                "data_inicio": start.isoformat() if start else None,
                "data_fim": end.isoformat() if end else None,
                "incluir_trecho": incluir_trecho,
            },
            consultado_em=datetime.now(UTC).isoformat(timespec="seconds"),
            avisos=avisos,
        )
    finally:
        con.close()
