"""Consulta ao dossiê de processo unificado via DuckDB (RFC 0014 M2).

Lê, por padrão, os dois parquets canônicos publicados no item IA
`causaganha-dashboard` (`processos_unificados.parquet` +
`processo_documentos.parquet`, produzidos por
`scripts/reconcile_processos.py`) — a mesma fonte, com a mesma projeção de
colunas e ordenação, que `web/src/lib/processoCnj.ts` usa para renderizar
`/processo?cnj=...`. Nenhum cache local nesta primeira versão: a decisão
(RFC 0014 M2) foi ler direto do Internet Archive, para que a tool funcione
numa instalação nova e nunca divirja do que o dashboard já publica.

Falhas são tratadas em duas categorias:
  - Não conseguir abrir `processos_unificados.parquet` é fatal — propaga a
    exceção do DuckDB/httpx para o chamador (a tool MCP a traduz em
    `ToolError`; não há resposta possível sem esse arquivo).
  - Não conseguir carregar `processo_documentos.parquet` ou
    `processos_unificados.report.json` é parcial — o processo já encontrado
    ainda é retornado, com a lista/lacuna correspondente vazia e um aviso em
    `avisos`, nunca uma exceção.
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
PROCESSOS_UNIFICADOS_URL = f"{IA_DASHBOARD_BASE}/processos_unificados.parquet"
PROCESSO_DOCUMENTOS_URL = f"{IA_DASHBOARD_BASE}/processo_documentos.parquet"
REPORT_URL = f"{IA_DASHBOARD_BASE}/processos_unificados.report.json"

_RELATORIO_INDISPONIVEL_AVISO = (
    "Relatório de cobertura (processos_unificados.report.json) indisponível; "
    "sem detalhamento de quais fontes estavam carregadas na geração do dataset."
)


def _unificado_sql(url: str) -> str:
    # `url` é sempre uma constante do módulo (ou um override explícito de
    # teste), nunca entrada do usuário — só o CNJ, abaixo, é bind parameter.
    return f"""
        SELECT
            nr_processo, nr_processo_mascara, fontes,
            djen_primeira_pub, djen_ultima_pub, djen_n_publicacoes, djen_tribunais,
            juris_n_documentos, juris_tipos, juris_data_julgamento,
            juris_orgao, juris_relator, juris_classe, juris_url,
            stj_id, stj_classe, stj_relator, stj_tema, stj_tese, stj_ementa,
            stj_data_decisao, stj_data_publicacao,
            classe_oficial, assuntos, orgao_julgador, grau,
            data_ajuizamento, ultima_atualizacao, tem_datajud,
            updated_at
        FROM read_parquet('{url}')
        WHERE nr_processo = ?
        LIMIT 1
    """  # noqa: S608


def _documentos_sql(url: str) -> str:
    return f"""
        SELECT fonte, id_documento, tipo, data, url, resumo
        FROM read_parquet('{url}')
        WHERE nr_processo = ?
        ORDER BY data DESC NULLS LAST, id_documento
        LIMIT ?
    """  # noqa: S608


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
    """Carrega `processos_unificados.report.json`; None quando indisponível/ilegível."""
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


def _load_httpfs_if_remote(con: duckdb.DuckDBPyConnection, url: str) -> None:
    if not url.startswith(("http://", "https://")):
        return
    # Deixa a query real abaixo falhar com um erro claro caso o httpfs seja
    # de fato necessário — mesmo padrão não-fatal usado em
    # scripts/reconcile_processos.py.
    with contextlib.suppress(duckdb.Error):
        con.execute("INSTALL httpfs; LOAD httpfs;")


def _mapear_linha(
    row: tuple[Any, ...],
) -> tuple[
    str,
    list[str],
    DjenResumo | None,
    JurisDecisao | None,
    StjAcordao | None,
    DatajudCapa | None,
    Any,
]:
    """Converte uma linha crua de `processos_unificados` nos sub-modelos por fonte."""
    (
        _nr_processo,
        nr_processo_mascara,
        fontes,
        djen_primeira_pub,
        djen_ultima_pub,
        djen_n_publicacoes,
        djen_tribunais,
        juris_n_documentos,
        juris_tipos,
        juris_data_julgamento,
        juris_orgao,
        juris_relator,
        juris_classe,
        juris_url,
        stj_id,
        stj_classe,
        stj_relator,
        stj_tema,
        stj_tese,
        stj_ementa,
        stj_data_decisao,
        stj_data_publicacao,
        classe_oficial,
        assuntos,
        orgao_julgador,
        grau,
        data_ajuizamento,
        ultima_atualizacao,
        tem_datajud,
        updated_at,
    ) = row

    fontes_presentes = list(fontes or [])

    djen = None
    if "djen" in fontes_presentes:
        djen = DjenResumo(
            primeira_publicacao=_iso(djen_primeira_pub),
            ultima_publicacao=_iso(djen_ultima_pub),
            n_publicacoes=djen_n_publicacoes,
            tribunais=list(djen_tribunais or []),
        )

    juris = None
    if "juris" in fontes_presentes:
        juris = JurisDecisao(
            n_documentos=juris_n_documentos,
            tipos=list(juris_tipos or []),
            data_julgamento=_iso(juris_data_julgamento),
            orgao=juris_orgao,
            relator=juris_relator,
            classe=juris_classe,
            url=juris_url,
        )

    stj = None
    if "stj" in fontes_presentes:
        stj = StjAcordao(
            id=stj_id,
            classe=stj_classe,
            relator=stj_relator,
            tema=stj_tema,
            tese=stj_tese,
            ementa=stj_ementa,
            data_decisao=_iso(stj_data_decisao),
            data_publicacao=_iso(stj_data_publicacao),
        )

    # tem_datajud é a fonte da verdade (RFC 0010); checar os dois é
    # redundante com a lista `fontes` mas inofensivo caso um dia divirjam —
    # mesma cautela de `web/src/lib/processoCnj.ts:mapProcessoRow`.
    datajud = None
    if "datajud" in fontes_presentes and tem_datajud:
        datajud = DatajudCapa(
            classe_oficial=classe_oficial,
            assuntos=assuntos,
            orgao_julgador=orgao_julgador,
            grau=grau,
            data_ajuizamento=_iso(data_ajuizamento),
            ultima_atualizacao=_iso(ultima_atualizacao),
        )

    return nr_processo_mascara, fontes_presentes, djen, juris, stj, datajud, updated_at


def _carregar_documentos(
    con: duckdb.DuckDBPyConnection,
    url: str,
    nr_processo: str,
    limite: int,
    avisos: list[str],
) -> tuple[list[DocumentoProcesso], bool]:
    """Busca até `limite` documentos; falha vira aviso, nunca exceção."""
    try:
        # limite+1 detecta "há mais" sem um COUNT(*) extra — mesmo padrão de
        # web/src/lib/processoCnj.ts:paginate.
        doc_rows = con.execute(_documentos_sql(url), [nr_processo, limite + 1]).fetchall()
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
    processos_url: str = PROCESSOS_UNIFICADOS_URL,
    documentos_url: str = PROCESSO_DOCUMENTOS_URL,
    report_url: str = REPORT_URL,
) -> ProcessoConsultaResult:
    """Busca o dossiê unificado de um CNJ nos parquets canônicos do IA.

    Levanta `CnjInvalidoError` para um CNJ malformado (nunca chega a abrir
    parquet nenhum). Propaga `duckdb.Error`/`httpx.HTTPError` quando
    `processos_unificados.parquet` em si não pode ser aberto — não há
    resposta possível sem ele. Falha ao carregar `processo_documentos.
    parquet` ou o relatório de cobertura vira resultado parcial (aviso +
    lacuna vazia), nunca propaga.
    """
    nr_processo = normalizar_cnj(cnj)
    if not nr_processo:
        msg = f"CNJ inválido (esperado 20 dígitos): {cnj!r}"
        raise CnjInvalidoError(msg)

    con = duckdb.connect()
    _load_httpfs_if_remote(con, processos_url)
    row = con.execute(_unificado_sql(processos_url), [nr_processo]).fetchone()

    avisos: list[str] = []
    cobertura_result = _carregar_cobertura(report_url)
    if cobertura_result is None:
        cobertura: list[FonteCobertura] = []
        dataset_gerado_em: str | None = None
        avisos.append(_RELATORIO_INDISPONIVEL_AVISO)
    else:
        cobertura, dataset_gerado_em = cobertura_result

    if row is None:
        return ProcessoConsultaResult(
            encontrado=False,
            nr_processo=nr_processo,
            nr_processo_mascara=formatar_cnj(nr_processo),
            cobertura_dataset=cobertura,
            dataset_gerado_em=dataset_gerado_em,
            avisos=avisos,
        )

    nr_processo_mascara, fontes_presentes, djen, juris, stj, datajud, updated_at = _mapear_linha(
        row
    )

    # O relatório não estava disponível (dataset_gerado_em ainda None) —
    # cai para o timestamp de geração desta própria linha.
    if dataset_gerado_em is None:
        dataset_gerado_em = _iso(updated_at)

    documentos: list[DocumentoProcesso] = []
    documentos_truncados = False
    if incluir_documentos:
        documentos, documentos_truncados = _carregar_documentos(
            con, documentos_url, nr_processo, limite_documentos, avisos
        )

    return ProcessoConsultaResult(
        encontrado=True,
        nr_processo=nr_processo,
        nr_processo_mascara=nr_processo_mascara or formatar_cnj(nr_processo),
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
