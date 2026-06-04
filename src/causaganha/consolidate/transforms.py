"""Ibis table builders: NDJSON → 10 normalized DuckDB tables.

The only raw SQL is ``read_json_auto``. Everything else (UUIDs, name
normalization, unnesting, deduplication) is pure Ibis. UDFs run per-row
inside DuckDB — no Python materialization until Parquet export.

Moved verbatim from ``scripts/pipeline/consolidate.py`` (lines 410-1084).
Splitting to its own module makes the consolidation pipeline's memory
hotspots (manifest loading, ZIP extraction) easier to isolate.
"""

from __future__ import annotations

import decimal


# Disable strict decimal traps that cause crashes in ibis/sqlglot
# See: https://github.com/ibis-project/ibis/issues/9638 (similar)
# Must happen before importing ibis.
decimal.getcontext().traps[decimal.InvalidOperation] = False

import unicodedata
import uuid
from typing import TYPE_CHECKING, Any

import ibis
import structlog

from causaganha.storage.djen_schema import (
    FIELD_CODIGO_CLASSE,
    FIELD_DATA_DISPONIBILIZACAO,
    FIELD_NOME_CLASSE,
    FIELD_NOME_ORGAO,
    FIELD_NUMERO_COMUNICACAO,
    FIELD_NUMERO_OAB,
    FIELD_NUMERO_PROCESSO,
    FIELD_TIPO_COMUNICACAO,
    FIELD_TIPO_DOCUMENTO,
    FIELD_UF_OAB,
)


if TYPE_CHECKING:
    from pathlib import Path


log = structlog.get_logger()

NAMESPACE_DJEN = uuid.uuid5(uuid.NAMESPACE_DNS, "djen.causaganha.org")


# ── Ibis scalar UDFs ────────────────────────────────────────────────


@ibis.udf.scalar.python
def djen_uuid5(s: str) -> str:
    """Deterministic UUIDv5 in the CausaGanha DJEN namespace."""
    if s is None:
        return None  # type: ignore[return-value]
    return str(uuid.uuid5(NAMESPACE_DJEN, s))


@ibis.udf.scalar.python
def normalize_name(s: str) -> str:
    """Strip accents, uppercase, collapse whitespace."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.upper().split())


# ── Ibis helpers (small composable building blocks) ─────────────────


def _safe(col: ibis.Column) -> ibis.Column:
    """Cast to string, strip whitespace, fill NULL with ''."""
    return col.cast("string").strip().fill_null("")


def _col(t: ibis.Table, *names: str) -> ibis.Column:
    """COALESCE the first existing columns by *names*, or literal(None).

    Casts all columns to string before coalescing to avoid type precedence errors
    when mixing date and string columns.
    """
    existing = [t[n].cast("string") for n in names if n in t.columns]
    if not existing:
        return ibis.literal(None)
    return ibis.coalesce(*existing) if len(existing) > 1 else existing[0]


def _struct_field(struct_col: ibis.Column, *names: str) -> ibis.Column:
    """Safely access first existing field from a struct (handles naming variants)."""
    field_names = struct_col.type().names
    for name in names:
        if name in field_names:
            return struct_col[name]
    return ibis.literal(None)


def _date_expr(raw: ibis.Table) -> ibis.Column:
    """Parse the availability date from either naming convention."""
    return _safe(_col(raw, *FIELD_DATA_DISPONIBILIZACAO)).left(10).try_cast("date")


def _com_id(raw: ibis.Table) -> ibis.Column:
    """Communication UUID: hash of DJEN original id + tribunal."""
    return djen_uuid5(_safe(raw.id) + ":" + raw.src_tribunal)


def _texto_id(raw: ibis.Table) -> ibis.Column:
    """Text UUID: content-addressed hash of the text itself."""
    txt = _safe(raw.texto)
    return ibis.cases((txt != "", djen_uuid5(txt)), else_="")


def _parte_id(d: ibis.Column) -> ibis.Column:
    """Party UUID: hash of normalized name."""
    return djen_uuid5(normalize_name(d["nome"].cast("string").fill_null("")))


def _adv_global_id(da: ibis.Column, tribunal: ibis.Column) -> ibis.Column:
    """Advogado UUID: prefer OAB+UF key, fall back to nome+tribunal+orig_id."""
    adv = da["advogado"]
    oab = _safe(_struct_field(adv, *FIELD_NUMERO_OAB))
    uf = _safe(_struct_field(adv, *FIELD_UF_OAB))
    nome = _safe(adv["nome"])
    orig_id = _safe(
        ibis.coalesce(
            _struct_field(adv, "id"),
            _struct_field(da, "advogado_id"),
        ),
    )
    return ibis.cases(
        ((oab != "") & (uf != ""), djen_uuid5(oab + ":" + uf)),
        else_=djen_uuid5(nome + ":" + tribunal + ":" + orig_id),
    )


def _partitions(raw: ibis.Table, item_id: str) -> dict[str, ibis.Expr]:
    """Common partitioning columns shared across most tables."""
    d = _date_expr(raw)
    return {
        "p_ano": d.year().fill_null(0).cast("int32"),
        "p_mes": d.month().fill_null(0).cast("int32"),
        "p_item_ia": ibis.literal(item_id),
    }


# ── Table builders — each returns a SELECT-style Ibis expression ────


def _build_comunicacoes(raw: ibis.Table, item_id: str) -> ibis.Table:
    return raw.select(
        id=_com_id(raw),
        original_id=_safe(raw.id),
        tribunal=raw.src_tribunal,
        numero_processo=_safe(_col(raw, *FIELD_NUMERO_PROCESSO)),
        numero_processo_mascara=_safe(_col(raw, "numeroprocessocommascara")),
        data_disponibilizacao=_date_expr(raw),
        tipo_comunicacao=_safe(_col(raw, *FIELD_TIPO_COMUNICACAO)),
        nome_orgao=_safe(_col(raw, *FIELD_NOME_ORGAO)),
        meio=_safe(_col(raw, "meio")),
        link=_safe(_col(raw, "link")),
        tipo_documento=_safe(_col(raw, *FIELD_TIPO_DOCUMENTO)),
        nome_classe=_safe(_col(raw, *FIELD_NOME_CLASSE)),
        codigo_classe=_safe(_col(raw, *FIELD_CODIGO_CLASSE)),
        numero_comunicacao=_safe(_col(raw, *FIELD_NUMERO_COMUNICACAO)),
        hash=_safe(_col(raw, "hash")),
        processed_at=ibis.now(),
        texto_id=_texto_id(raw),
        **_partitions(raw, item_id),
    )


def _build_textos(raw: ibis.Table, _item_id: str) -> ibis.Table:
    txt = _safe(raw.texto)
    return (
        raw.filter(txt != "")
        .select(
            id=djen_uuid5(txt),
            texto=txt,
        )
        .distinct()
    )


def _build_destinatarios(raw: ibis.Table, item_id: str) -> ibis.Table:
    t = raw.select(
        com_key=_safe(raw.id) + ":" + raw.src_tribunal,
        src_tribunal=raw.src_tribunal,
        disp_date=_date_expr(raw),
        src_item_id=ibis.literal(item_id),
        d=raw.destinatarios.unnest(),
    )
    return t.select(
        comunicacao_id=djen_uuid5(t.com_key),
        tribunal=t.src_tribunal,
        nome=_safe(t.d["nome"]),
        polo=_safe(t.d["polo"]),
        parte_id=_parte_id(t.d),
        p_ano=t.disp_date.year().fill_null(0).cast("int32"),
        p_mes=t.disp_date.month().fill_null(0).cast("int32"),
        p_item_ia=t.src_item_id,
    )


def _build_partes(raw: ibis.Table, _item_id: str) -> ibis.Table:
    t = raw.select(d=raw.destinatarios.unnest())
    nome_norm = normalize_name(t.d["nome"].cast("string").fill_null(""))
    return (
        t.filter(nome_norm != "")
        .select(
            id=djen_uuid5(nome_norm),
            nome_normalizado=nome_norm,
            nome_original=_safe(t.d["nome"]),
        )
        .distinct(on="id")
    )


def _build_comunicacao_advogados(raw: ibis.Table, _item_id: str) -> ibis.Table:
    t = raw.select(
        com_key=_safe(raw.id) + ":" + raw.src_tribunal,
        src_tribunal=raw.src_tribunal,
        da=raw.destinatarioadvogados.unnest(),
    )
    return t.select(
        comunicacao_id=djen_uuid5(t.com_key),
        tribunal=t.src_tribunal,
        advogado_id=_adv_global_id(t.da, t.src_tribunal),
    )


def _build_advogados(raw: ibis.Table, item_id: str) -> ibis.Table:
    t = raw.select(
        src_tribunal=raw.src_tribunal,
        disp_date=_date_expr(raw),
        src_item_id=ibis.literal(item_id),
        da=raw.destinatarioadvogados.unnest(),
    )
    adv = t.da["advogado"]
    return t.filter(adv.notnull()).select(
        id=_adv_global_id(t.da, t.src_tribunal),
        original_id=_safe(
            ibis.coalesce(_struct_field(adv, "id"), _struct_field(t.da, "advogado_id")),
        ),
        tribunal=t.src_tribunal,
        nome=_safe(adv["nome"]),
        numero_oab=_safe(_struct_field(adv, *FIELD_NUMERO_OAB)),
        uf_oab=_safe(_struct_field(adv, *FIELD_UF_OAB)),
        p_ano=t.disp_date.year().fill_null(0).cast("int32"),
        p_mes=t.disp_date.month().fill_null(0).cast("int32"),
        p_item_ia=t.src_item_id,
    )


def _build_advogado_nomes(raw: ibis.Table, _item_id: str) -> ibis.Table:
    t = raw.select(
        src_tribunal=raw.src_tribunal,
        disp_date=_date_expr(raw),
        da=raw.destinatarioadvogados.unnest(),
    )
    adv = t.da["advogado"]
    return t.filter(adv.notnull()).select(
        advogado_id=_adv_global_id(t.da, t.src_tribunal),
        nome=_safe(adv["nome"]),
        tribunal=t.src_tribunal,
        first_seen=t.disp_date,
    )


def _build_representacoes(raw: ibis.Table, item_id: str) -> ibis.Table:
    step1 = raw.select(
        com_key=_safe(raw.id) + ":" + raw.src_tribunal,
        src_tribunal=raw.src_tribunal,
        disp_date=_date_expr(raw),
        src_item_id=ibis.literal(item_id),
        d=raw.destinatarios.unnest(),
        destinatarioadvogados=raw.destinatarioadvogados,
    )
    step2 = step1.select(
        step1.com_key,
        step1.src_tribunal,
        step1.disp_date,
        step1.src_item_id,
        step1.d,
        da=step1.destinatarioadvogados.unnest(),
    )
    adv = step2.da["advogado"]
    return step2.filter(adv.notnull()).select(
        comunicacao_id=djen_uuid5(step2.com_key),
        tribunal=step2.src_tribunal,
        advogado_id=_adv_global_id(step2.da, step2.src_tribunal),
        parte_id=_parte_id(step2.d),
        polo=_safe(step2.d["polo"]),
        p_ano=step2.disp_date.year().fill_null(0).cast("int32"),
        p_mes=step2.disp_date.month().fill_null(0).cast("int32"),
        p_item_ia=step2.src_item_id,
    )


def _build_processos(raw: ibis.Table, item_id: str) -> ibis.Table:
    return raw.select(
        numero_processo=_safe(_col(raw, *FIELD_NUMERO_PROCESSO)),
        tribunal=raw.src_tribunal,
        data=_date_expr(raw),
        comunicacao_id=_com_id(raw),
        **_partitions(raw, item_id),
    )


def _build_classificacoes(raw: ibis.Table, _item_id: str) -> ibis.Table:
    """Build classificacoes table — keyword-based outcome classification."""
    txt = _safe(raw.texto)
    txt_lower = txt.lower()
    texto_id = djen_uuid5(txt)

    has_text = txt != ""

    # Order matters: check "parcialmente procedente" before "procedente"
    outcome = ibis.cases(
        (txt_lower.contains("parcialmente procedente"), "PARTIAL"),
        (txt_lower.contains("improcedente"), "LOSS"),
        (txt_lower.contains("procedente"), "WIN"),
        (txt_lower.contains("acordo") | txt_lower.contains("transação"), "SETTLEMENT"),
        else_="UNKNOWN",
    )

    decision_type = ibis.cases(
        (txt_lower.contains("acórdão") | txt_lower.contains("acordão"), "acórdão"),
        (txt_lower.contains("sentença"), "sentença"),
        (txt_lower.contains("decisão interlocutória"), "decisão interlocutória"),
        else_="outro",
    )

    confidence = ibis.literal(0.3).cast("float64")

    return (
        raw.filter(has_text)
        .filter(outcome != "UNKNOWN")
        .select(
            texto_id=texto_id,
            metodo=ibis.literal("keyword_v1"),
            outcome=outcome,
            decision_type=decision_type,
            winner_advogado_id=ibis.null().cast("string"),
            loser_advogado_id=ibis.null().cast("string"),
            confidence=confidence,
            classified_at=ibis.now(),
        )
        .distinct(on=["texto_id"])
    )


# Ordered list: tables with FK dependencies come after their parents.
_TABLE_BUILDERS: tuple[tuple[str, Any], ...] = (
    ("comunicacoes", _build_comunicacoes),
    ("textos", _build_textos),
    ("destinatarios", _build_destinatarios),
    ("partes", _build_partes),
    ("comunicacao_advogados", _build_comunicacao_advogados),
    ("advogados", _build_advogados),
    ("advogado_nomes", _build_advogado_nomes),
    ("representacoes", _build_representacoes),
    ("processos", _build_processos),
    ("classificacoes", _build_classificacoes),
)


# ── Schemas ─────────────────────────────────────────────────────────


TABLE_SCHEMAS = {
    "comunicacoes": ibis.schema(
        {
            "id": "string",
            "original_id": "string",
            "tribunal": "string",
            "numero_processo": "string",
            "numero_processo_mascara": "string",
            "data_disponibilizacao": "date",
            "tipo_comunicacao": "string",
            "nome_orgao": "string",
            "meio": "string",
            "link": "string",
            "tipo_documento": "string",
            "nome_classe": "string",
            "codigo_classe": "string",
            "numero_comunicacao": "string",
            "hash": "string",
            "processed_at": "timestamp",
            "texto_id": "string",
            "p_ano": "int32",
            "p_mes": "int32",
            "p_item_ia": "string",
        },
    ),
    "advogados": ibis.schema(
        {
            "id": "string",
            "original_id": "string",
            "tribunal": "string",
            "nome": "string",
            "numero_oab": "string",
            "uf_oab": "string",
            "p_ano": "int32",
            "p_mes": "int32",
            "p_item_ia": "string",
        },
    ),
    "advogado_nomes": ibis.schema(
        {
            "advogado_id": "string",
            "nome": "string",
            "tribunal": "string",
            "first_seen": "date",
        },
    ),
    "destinatarios": ibis.schema(
        {
            "comunicacao_id": "string",
            "tribunal": "string",
            "nome": "string",
            "polo": "string",
            "parte_id": "string",
            "p_ano": "int32",
            "p_mes": "int32",
            "p_item_ia": "string",
        },
    ),
    "comunicacao_advogados": ibis.schema(
        {
            "comunicacao_id": "string",
            "tribunal": "string",
            "advogado_id": "string",
        },
    ),
    "textos": ibis.schema(
        {
            "id": "string",
            "texto": "string",
        },
    ),
    "representacoes": ibis.schema(
        {
            "comunicacao_id": "string",
            "tribunal": "string",
            "advogado_id": "string",
            "parte_id": "string",
            "polo": "string",
            "p_ano": "int32",
            "p_mes": "int32",
            "p_item_ia": "string",
        },
    ),
    "processos": ibis.schema(
        {
            "numero_processo": "string",
            "tribunal": "string",
            "data": "date",
            "comunicacao_id": "string",
            "p_ano": "int32",
            "p_mes": "int32",
            "p_item_ia": "string",
        },
    ),
    "classificacoes": ibis.schema(
        {
            "texto_id": "string",
            "metodo": "string",
            "outcome": "string",
            "decision_type": "string",
            "winner_advogado_id": "string",
            "loser_advogado_id": "string",
            "confidence": "float64",
            "classified_at": "timestamp",
        },
    ),
    "partes": ibis.schema(
        {
            "id": "string",
            "nome_normalizado": "string",
            "nome_original": "string",
        },
    ),
}
TABLES = list(TABLE_SCHEMAS.keys())


def init_tables(con: ibis.BaseBackend) -> None:
    """Initialize tables with correct schema using Ibis."""
    for table, schema in TABLE_SCHEMAS.items():
        con.create_table(table, schema=schema, overwrite=True)


def load_and_transform(
    con: ibis.BaseBackend,
    ndjson_dir: Path,
    item_id: str,
) -> dict[str, int]:
    """Load raw per-tribunal NDJSON into DuckDB, produce all 10 tables via Ibis.

    The only raw SQL is ``read_json_auto`` (DuckDB-specific loader). Everything
    else — UUIDs, name normalization, unnesting, deduplication — is expressed
    as Ibis table expressions executed by the DuckDB backend.
    """
    con.raw_sql(
        f"CREATE OR REPLACE TABLE _staging AS "
        f"SELECT * FROM read_json_auto('{ndjson_dir}/*.ndjson', "
        f"filename=true, union_by_name=true)",
    )
    staging = con.table("_staging")

    raw_expr = staging.mutate(
        src_tribunal=staging.filename.split("/")[-1].split("__")[0],
        src_item_id=ibis.literal(item_id),
    )
    con.create_table("raw_records", raw_expr, overwrite=True)
    raw = con.table("raw_records")

    counts: dict[str, int] = {}
    for table_name, builder in _TABLE_BUILDERS:
        expr = builder(raw, item_id)
        con.insert(table_name, expr)
        row_count = con.table(table_name).count().execute()
        counts[table_name] = row_count
        if row_count:
            log.info("table_populated", table=table_name, rows=row_count)

    con.drop_table("raw_records", force=True)
    con.drop_table("_staging", force=True)
    return counts
