"""Consulta ao dossiê de processo unificado via DuckDB (RFC 0014 M2).

Lê, por padrão, `indice_processual.parquet` — o índice fino publicado no
item IA `causaganha-dashboard` por `scripts/reconcile_processos.py` — para
descobrir quais fontes (DJEN/JURIS/STJ/DataJud) têm registro para um CNJ e
em qual arquivo cada registro vive (`arquivo_ia_url`). O dossiê em si é
montado consultando os parquets de origem (`comunicacoes.parquet`,
`tjro-juris-{ano}.parquet`, `stj-acordaos.parquet`, `datajud-capa-
{tribunal}.parquet`) diretamente — o índice nunca guarda cópia dos campos de
conteúdo (generaliza o padrão que a própria tabela `processos` do DJEN já
usava; ver `causaganha/consolidate/schema_registry.py`).

Nenhum cache local nesta primeira versão: a decisão (RFC 0014 M2) foi ler
direto do Internet Archive, para que a tool funcione numa instalação nova e
nunca divirja do que o dashboard já publica (mesma semântica de
`web/src/lib/processoCnj.ts`).

Falhas são tratadas em duas categorias:
  - Não conseguir abrir `indice_processual.parquet` é fatal — propaga a
    exceção do DuckDB/httpx para o chamador (a tool MCP a traduz em
    `ToolError`; não há resposta possível sem esse arquivo).
  - Não conseguir carregar um parquet de origem específico ou o relatório de
    cobertura (`indice_processual.report.json`) é parcial — o processo já
    encontrado ainda é retornado, com a lacuna correspondente vazia e um
    aviso em `avisos`, nunca uma exceção.
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

import duckdb
import httpx

from causaganha.processos.cnj import formatar_cnj, normalizar_cnj
from causaganha.processos.models import (
    CnjInvalidoError,
    DatajudCapa,
    DjenResumo,
    DocumentoProcesso,
    FonteCobertura,
    JurisDecisao,
    ProcessoConsultaResult,
    StjAcordao,
)


IA_DASHBOARD_BASE = "https://archive.org/download/causaganha-dashboard"
INDICE_PROCESSUAL_URL = f"{IA_DASHBOARD_BASE}/indice_processual.parquet"
REPORT_URL = f"{IA_DASHBOARD_BASE}/indice_processual.report.json"

_RELATORIO_INDISPONIVEL_AVISO = (
    "Relatório de cobertura (indice_processual.report.json) indisponível; "
    "sem detalhamento de quais fontes estavam carregadas na geração do dataset."
)


def _url_list_sql(urls: list[str]) -> str:
    return ", ".join(f"'{u}'" for u in urls)


def _indice_sql(url: str) -> str:
    # `url` é sempre uma constante do módulo (ou um override explícito de
    # teste), nunca entrada do usuário — só o CNJ, abaixo, é bind parameter.
    return f"""
        SELECT fonte, arquivo_ia_url
        FROM read_parquet('{url}')
        WHERE numero_processo = ?
    """


def _djen_sql(urls: list[str]) -> str:
    return f"""
        SELECT
            COUNT(*)::INTEGER AS n_publicacoes,
            MIN(data_disponibilizacao)::DATE AS primeira_publicacao,
            MAX(data_disponibilizacao)::DATE AS ultima_publicacao,
            list(DISTINCT tribunal) AS tribunais
        FROM read_parquet([{_url_list_sql(urls)}], union_by_name=true)
        WHERE regexp_replace(numero_processo, '[^0-9]', '', 'g') = ?
    """


def _juris_sql(urls: list[str]) -> str:
    return f"""
        WITH cleaned AS (
            SELECT id_documento, tipo, data_julgamento, orgao, relator, classe_judicial, url_portal
            FROM read_parquet([{_url_list_sql(urls)}])
            WHERE regexp_replace(nr_processo, '[^0-9]', '', 'g') = ?
        ),
        ranked AS (
            SELECT *, ROW_NUMBER() OVER (
                ORDER BY
                    CASE tipo WHEN 'ACÓRDÃO' THEN 1 WHEN 'SENTENÇA' THEN 2 ELSE 9 END,
                    data_julgamento DESC NULLS LAST
            ) AS rn
            FROM cleaned
        ),
        principal AS (SELECT * FROM ranked WHERE rn = 1),
        agg AS (
            SELECT
                COUNT(*)::INTEGER AS n_documentos,
                list(DISTINCT tipo) AS tipos,
                MAX(data_julgamento) AS data_julgamento
            FROM cleaned
        )
        SELECT
            agg.n_documentos, agg.tipos, agg.data_julgamento::DATE AS data_julgamento,
            principal.orgao, principal.relator,
            principal.classe_judicial AS classe, principal.url_portal AS url
        FROM agg, principal
    """


def _stj_sql(urls: list[str]) -> str:
    return f"""
        SELECT
            COUNT(*)::INTEGER AS n,
            FIRST(id ORDER BY "dataDecisao" DESC NULLS LAST)::VARCHAR AS id,
            FIRST("siglaClasse" ORDER BY "dataDecisao" DESC NULLS LAST) AS classe,
            FIRST("ministroRelator" ORDER BY "dataDecisao" DESC NULLS LAST) AS relator,
            FIRST("tema" ORDER BY "dataDecisao" DESC NULLS LAST)::VARCHAR AS tema,
            FIRST("teseJuridica" ORDER BY "dataDecisao" DESC NULLS LAST) AS tese,
            FIRST("ementa" ORDER BY "dataDecisao" DESC NULLS LAST) AS ementa,
            MAX("dataDecisao")::DATE AS data_decisao,
            MAX("dataPublicacao")::DATE AS data_publicacao
        FROM read_parquet([{_url_list_sql(urls)}])
        WHERE regexp_replace("numeroProcesso", '[^0-9]', '', 'g') = ?
    """


def _datajud_sql(urls: list[str]) -> str:
    return f"""
        SELECT
            COUNT(*)::INTEGER AS n,
            FIRST(classe_nome ORDER BY ultima_atualizacao DESC NULLS LAST) AS classe_oficial,
            FIRST(assuntos ORDER BY ultima_atualizacao DESC NULLS LAST) AS assuntos,
            FIRST(orgao_julgador ORDER BY ultima_atualizacao DESC NULLS LAST) AS orgao_julgador,
            FIRST(grau ORDER BY ultima_atualizacao DESC NULLS LAST) AS grau,
            MIN(data_ajuizamento) AS data_ajuizamento,
            MAX(ultima_atualizacao) AS ultima_atualizacao
        FROM read_parquet([{_url_list_sql(urls)}])
        WHERE numero_processo = ?
    """


def _documentos_sql(juris_urls: list[str], stj_urls: list[str]) -> tuple[str, int]:
    """Returns (sql, n_cnj_params) — one `?` per source branch present, before the LIMIT `?`."""
    parts = []
    if juris_urls:
        parts.append(f"""
            SELECT 'juris' AS fonte, id_documento::VARCHAR AS id_documento, tipo,
                data_julgamento::DATE AS data, url_portal AS url,
                left(texto_limpo, 500) AS resumo
            FROM read_parquet([{_url_list_sql(juris_urls)}])
            WHERE regexp_replace(nr_processo, '[^0-9]', '', 'g') = ?
        """)
    if stj_urls:
        parts.append(f"""
            SELECT 'stj' AS fonte, id::VARCHAR AS id_documento, "siglaClasse" AS tipo,
                "dataDecisao"::DATE AS data, '' AS url, left("ementa", 500) AS resumo
            FROM read_parquet([{_url_list_sql(stj_urls)}])
            WHERE regexp_replace("numeroProcesso", '[^0-9]', '', 'g') = ?
        """)
    union = " UNION ALL ".join(parts)
    return f"{union} ORDER BY data DESC NULLS LAST, id_documento LIMIT ?", len(parts)


def _iso(value: Any) -> str | None:  # noqa: ANN401 — DuckDB row values are untyped at this layer
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _fetch_text(url_or_path: str) -> str:
    if url_or_path.startswith(("http://", "https://")):
        resp = httpx.get(url_or_path, timeout=10.0)
        resp.raise_for_status()
        return resp.text
    return Path(url_or_path).read_text(encoding="utf-8")


def _carregar_cobertura(report_url: str) -> tuple[list[FonteCobertura], str | None] | None:
    """Carrega `indice_processual.report.json`; None quando indisponível/ilegível."""
    try:
        raw = _fetch_text(report_url)
        data = json.loads(raw)
    except (OSError, httpx.HTTPError, json.JSONDecodeError):
        return None
    cobertura = [
        FonteCobertura(fonte=nome, status=fonte["status"], registros=fonte["rows"])
        for nome, fonte in data.get("sources", {}).items()
    ]
    return cobertura, data.get("generated_at")


def _fonte_urls(rows: list[tuple[str, str]], fonte: str) -> list[str]:
    return sorted({url for row_fonte, url in rows if row_fonte == fonte})


def _load_httpfs(con: duckdb.DuckDBPyConnection) -> None:
    # INSTALL/LOAD httpfs is idempotent and cheap once already loaded, so
    # this is always called unconditionally rather than trying to predict
    # whether any of the URLs about to be queried are remote.
    with contextlib.suppress(duckdb.Error):
        con.execute("INSTALL httpfs; LOAD httpfs;")


def _fonte_indisponivel_aviso(fonte: str, exc: duckdb.Error) -> str:
    return f"Fonte '{fonte}' indisponível para este processo: {exc}"


def _build_djen(
    con: duckdb.DuckDBPyConnection, urls: list[str], cnj: str, avisos: list[str]
) -> DjenResumo | None:
    if not urls:
        return None
    try:
        row = con.execute(_djen_sql(urls), [cnj]).fetchone()
    except duckdb.Error as exc:
        avisos.append(_fonte_indisponivel_aviso("djen", exc))
        return None
    if row is None or row[0] == 0:
        return None
    n_publicacoes, primeira, ultima, tribunais = row
    return DjenResumo(
        primeira_publicacao=_iso(primeira),
        ultima_publicacao=_iso(ultima),
        n_publicacoes=n_publicacoes,
        tribunais=list(tribunais or []),
    )


def _build_juris(
    con: duckdb.DuckDBPyConnection, urls: list[str], cnj: str, avisos: list[str]
) -> JurisDecisao | None:
    if not urls:
        return None
    try:
        row = con.execute(_juris_sql(urls), [cnj]).fetchone()
    except duckdb.Error as exc:
        avisos.append(_fonte_indisponivel_aviso("juris", exc))
        return None
    if row is None:
        return None
    n_documentos, tipos, data_julgamento, orgao, relator, classe, url = row
    return JurisDecisao(
        n_documentos=n_documentos,
        tipos=list(tipos or []),
        data_julgamento=_iso(data_julgamento),
        orgao=orgao,
        relator=relator,
        classe=classe,
        url=url,
    )


def _build_stj(
    con: duckdb.DuckDBPyConnection, urls: list[str], cnj: str, avisos: list[str]
) -> StjAcordao | None:
    if not urls:
        return None
    try:
        row = con.execute(_stj_sql(urls), [cnj]).fetchone()
    except duckdb.Error as exc:
        avisos.append(_fonte_indisponivel_aviso("stj", exc))
        return None
    if row is None or row[0] == 0:
        return None
    _n, id_, classe, relator, tema, tese, ementa, data_decisao, data_publicacao = row
    return StjAcordao(
        id=id_,
        classe=classe,
        relator=relator,
        tema=tema,
        tese=tese,
        ementa=ementa,
        data_decisao=_iso(data_decisao),
        data_publicacao=_iso(data_publicacao),
    )


def _build_datajud(
    con: duckdb.DuckDBPyConnection, urls: list[str], cnj: str, avisos: list[str]
) -> DatajudCapa | None:
    if not urls:
        return None
    try:
        row = con.execute(_datajud_sql(urls), [cnj]).fetchone()
    except duckdb.Error as exc:
        avisos.append(_fonte_indisponivel_aviso("datajud", exc))
        return None
    if row is None or row[0] == 0:
        return None
    _n, classe_oficial, assuntos, orgao_julgador, grau, data_ajuizamento, ultima_atualizacao = row
    return DatajudCapa(
        classe_oficial=classe_oficial,
        assuntos=assuntos,
        orgao_julgador=orgao_julgador,
        grau=grau,
        data_ajuizamento=_iso(data_ajuizamento),
        ultima_atualizacao=_iso(ultima_atualizacao),
    )


def _build_documentos(
    con: duckdb.DuckDBPyConnection,
    juris_urls: list[str],
    stj_urls: list[str],
    cnj: str,
    limite: int,
    avisos: list[str],
) -> tuple[list[DocumentoProcesso], bool]:
    """Busca até `limite` documentos (JURIS + STJ); falha vira aviso, nunca exceção."""
    if not juris_urls and not stj_urls:
        return [], False
    sql, n_params = _documentos_sql(juris_urls, stj_urls)
    try:
        # limite+1 detecta "há mais" sem um COUNT(*) extra — mesmo padrão de
        # web/src/lib/processoCnj.ts:paginate.
        doc_rows = con.execute(sql, [cnj] * n_params + [limite + 1]).fetchall()
    except duckdb.Error as exc:
        avisos.append(f"Não foi possível carregar os documentos deste processo: {exc}")
        return [], False

    truncados = len(doc_rows) > limite
    documentos = [
        DocumentoProcesso(
            fonte=doc_fonte,
            id_documento=str(id_documento),
            tipo=tipo,
            data=_iso(data),
            url=url_doc,
            resumo=resumo,
        )
        for doc_fonte, id_documento, tipo, data, url_doc, resumo in doc_rows[:limite]
    ]
    return documentos, truncados


def buscar_processo(
    cnj: str,
    *,
    incluir_documentos: bool = True,
    limite_documentos: int = 10,
    indice_url: str = INDICE_PROCESSUAL_URL,
    report_url: str = REPORT_URL,
) -> ProcessoConsultaResult:
    """Busca o dossiê unificado de um CNJ via `indice_processual.parquet` + fontes de origem.

    Levanta `CnjInvalidoError` para um CNJ malformado (nunca chega a abrir
    parquet nenhum). Propaga `duckdb.Error`/`httpx.HTTPError` quando
    `indice_processual.parquet` em si não pode ser aberto — não há resposta
    possível sem ele. Falha ao carregar um parquet de origem específico ou o
    relatório de cobertura vira resultado parcial (aviso + lacuna vazia),
    nunca propaga.
    """
    nr_processo = normalizar_cnj(cnj)
    if not nr_processo:
        msg = f"CNJ inválido (esperado 20 dígitos): {cnj!r}"
        raise CnjInvalidoError(msg)

    with duckdb.connect() as con:
        _load_httpfs(con)

        rows = con.execute(_indice_sql(indice_url), [nr_processo]).fetchall()

        avisos: list[str] = []
        cobertura_result = _carregar_cobertura(report_url)
        if cobertura_result is None:
            cobertura: list[FonteCobertura] = []
            dataset_gerado_em: str | None = None
            avisos.append(_RELATORIO_INDISPONIVEL_AVISO)
        else:
            cobertura, dataset_gerado_em = cobertura_result

        if not rows:
            return ProcessoConsultaResult(
                encontrado=False,
                nr_processo=nr_processo,
                nr_processo_mascara=formatar_cnj(nr_processo),
                cobertura_dataset=cobertura,
                dataset_gerado_em=dataset_gerado_em,
                avisos=avisos,
            )

        fontes_presentes = sorted({fonte for fonte, _url in rows})
        djen_urls = _fonte_urls(rows, "djen")
        juris_urls = _fonte_urls(rows, "juris")
        stj_urls = _fonte_urls(rows, "stj")
        datajud_urls = _fonte_urls(rows, "datajud")

        djen = _build_djen(con, djen_urls, nr_processo, avisos)
        juris = _build_juris(con, juris_urls, nr_processo, avisos)
        stj = _build_stj(con, stj_urls, nr_processo, avisos)
        datajud = _build_datajud(con, datajud_urls, nr_processo, avisos)

        # Sem relatório, dataset_gerado_em fica None — o índice não guarda um
        # timestamp por linha (é fino por design), então não há fallback de
        # "geração" possível aqui como havia na versão de tabela larga; o
        # aviso do relatório indisponível já cobre essa lacuna.

        documentos: list[DocumentoProcesso] = []
        documentos_truncados = False
        if incluir_documentos:
            documentos, documentos_truncados = _build_documentos(
                con, juris_urls, stj_urls, nr_processo, limite_documentos, avisos
            )

    return ProcessoConsultaResult(
        encontrado=True,
        nr_processo=nr_processo,
        nr_processo_mascara=formatar_cnj(nr_processo),
        fontes_presentes=fontes_presentes,
        cobertura_dataset=cobertura,
        djen=djen,
        juris=juris,
        stj=stj,
        datajud=datajud,
        documentos=documentos,
        documentos_truncados=documentos_truncados,
        dataset_gerado_em=dataset_gerado_em,
        avisos=avisos,
    )
