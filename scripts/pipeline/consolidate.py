#!/usr/bin/env python3
"""Consolidate DJEN ZIP files into daily Parquet files.

This script downloads all ZIP files for a specific date from Internet Archive,
converts them to consolidated Parquet files (one per table type, all tribunals),
and uploads them back to IA.

Usage:
    # Consolidate specific date
    python scripts/pipeline/consolidate.py --date 2026-01-27

    # Dry run (don't upload)
    python scripts/pipeline/consolidate.py --date 2026-01-27 --dry-run
"""

import argparse
import decimal
import json
import os
import subprocess
import tempfile
import time
import unicodedata
import uuid
import zipfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any


# Disable strict decimal traps that cause crashes in ibis/sqlglot
# See: https://github.com/ibis-project/ibis/issues/9638 (similar)
# This is required because sqlglot may attempt to convert "binary_double_nan"
# which triggers InvalidOperation if traps are enabled.
decimal.getcontext().traps[decimal.InvalidOperation] = False

import httpx  # noqa: E402
import ibis  # noqa: E402
import structlog  # noqa: E402

from causaganha.config import TRIBUNAIS  # noqa: E402
from causaganha.storage.djen_schema import (  # noqa: E402
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


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCHEMA_VERSION = "3"
NAMESPACE_DJEN = uuid.uuid5(uuid.NAMESPACE_DNS, "djen.causaganha.org")

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Ibis scalar UDFs — the only Python called per-row during SQL execution.
# ---------------------------------------------------------------------------
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


# Table types to consolidate - Defined below via TABLE_SCHEMAS


def list_local_zips(directory: str) -> tuple[list[dict[str, Any]], int]:
    """Find all ZIP files in a local directory."""
    logger.info("listing_local_zips", directory=directory)
    zips: list[dict[str, Any]] = []
    local_dir = Path(directory)

    if not local_dir.exists():
        logger.warning("local_zips_not_found", directory=directory)
        return zips, 0

    for zip_file in local_dir.glob("*.zip"):
        # Extract tribunal from filename: djen-2026-01-23-TJSP.zip
        parts = zip_file.stem.split("-")
        tribunal = parts[-1] if len(parts) >= 4 else "UNKNOWN"
        zips.append(
            {
                "filename": zip_file.name,
                "tribunal": tribunal,
                "item_id": "local-test",
                "size": zip_file.stat().st_size,
                "local_path": str(zip_file),
            },
        )

    return zips, len(zips)


def list_zips_for_date(date: str) -> tuple[list[dict[str, Any]], int]:
    """Find all ZIP files for a specific date on IA using HTTP API."""
    logger.info("listing_zips", date=date)
    item_id = f"djen-{date}"
    zips: list[dict[str, Any]] = []

    try:
        # Use IA metadata API
        url = f"https://archive.org/metadata/{item_id}"
        response = httpx.get(url, timeout=60)

        if response.status_code == 200:
            data = response.json()
            files = data.get("files", [])

            # Identify what's on IA
            present = set()
            for file_info in files:
                filename = file_info.get("name", "")
                if filename.endswith((".zip", ".absent")):
                    parts = filename.replace(".zip", "").replace(".absent", "").split("-")
                    tribunal = parts[-1] if len(parts) >= 4 else "UNKNOWN"
                    present.add(tribunal)

                    if filename.endswith(".zip"):
                        zips.append(
                            {
                                "filename": filename,
                                "tribunal": tribunal,
                                "item_id": item_id,
                                "size": file_info.get("size", 0),
                            },
                        )

            # Return both zip list and completion status
            return zips, len(present)
        logger.warning("metadata_fetch_failed", item_id=item_id, status=response.status_code)

    except Exception as e:
        logger.warning("list_failed", item_id=item_id, error=str(e))

    logger.info("zips_found", count=len(zips), date=date)
    return zips, 0


def download_zip(item_id: str, filename: str, output_path: Path) -> bool:
    """Download ZIP from Internet Archive using httpx with retries."""
    url = f"https://archive.org/download/{item_id}/{filename}"
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=300) as response:
                if response.status_code == 200:
                    with output_path.open("wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                    return output_path.exists() and output_path.stat().st_size > 0
                if response.status_code in [502, 503, 504]:
                    logger.warning(
                        "download_server_error",
                        filename=filename,
                        status=response.status_code,
                        attempt=attempt + 1,
                    )
                    time.sleep(2**attempt)  # Exponential backoff
                    continue
                logger.warning(
                    "download_http_error",
                    filename=filename,
                    status=response.status_code,
                )
                return False
        except Exception as e:
            logger.warning("download_failed", filename=filename, error=str(e), attempt=attempt + 1)
            time.sleep(2**attempt)
    return False


def extract_json_from_zip(zip_path: Path) -> list[dict[str, Any]]:
    """Extract and parse JSON data from ZIP file."""
    records: list[dict[str, Any]] = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                if name.endswith(".json"):
                    try:
                        content = zf.read(name).decode("utf-8")
                        data = json.loads(content)
                        if isinstance(data, list):
                            records.extend(data)
                        elif isinstance(data, dict):
                            # Handle wrapped items or direct communication
                            if "items" in data and isinstance(data["items"], list):
                                records.extend(data["items"])
                            else:
                                records.append(data)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
    except zipfile.BadZipFile:
        logger.warning("bad_zip_file", path=str(zip_path))
    return records


# ---------------------------------------------------------------------------
# Ibis helpers — small composable building blocks for the table builders.
# ---------------------------------------------------------------------------


def _safe(col: ibis.Column) -> ibis.Column:
    """Cast to string, strip whitespace, fill NULL with ''."""
    return col.cast("string").strip().fill_null("")


def _col(t: ibis.Table, *names: str) -> ibis.Column:
    """COALESCE the first existing columns by *names*, or literal(None)."""
    existing = [t[n] for n in names if n in t.columns]
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
    return ibis.case().when(txt != "", djen_uuid5(txt)).else_("").end()


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
    return (
        ibis.case()
        .when((oab != "") & (uf != ""), djen_uuid5(oab + ":" + uf))
        .else_(djen_uuid5(nome + ":" + tribunal + ":" + orig_id))
        .end()
    )


def _partitions(raw: ibis.Table, item_id: str) -> dict[str, ibis.Expr]:
    """Common partitioning columns shared across most tables."""
    d = _date_expr(raw)
    return {
        "p_ano": d.year().fill_null(0).cast("int32"),
        "p_mes": d.month().fill_null(0).cast("int32"),
        "p_item_ia": ibis.literal(item_id),
    }


# ---------------------------------------------------------------------------
# Table builders — each returns an Ibis expression that SELECT-s into its
# target table.  No raw SQL.  UUIDs computed via the djen_uuid5() UDF,
# name normalization via normalize_name() UDF, flattening via .unnest().
# ---------------------------------------------------------------------------


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
    return t.filter(adv.notna()).select(
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
    return t.filter(adv.notna()).select(
        advogado_id=_adv_global_id(t.da, t.src_tribunal),
        nome=_safe(adv["nome"]),
        tribunal=t.src_tribunal,
        first_seen=t.disp_date,
    )


def _build_representacoes(raw: ibis.Table, item_id: str) -> ibis.Table:
    # Cross-join: unnest destinatarios, then unnest destinatarioadvogados
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
    return step2.filter(adv.notna()).select(
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
)


def _load_and_transform(
    con: ibis.BaseBackend,
    ndjson_dir: Path,
    item_id: str,
) -> dict[str, int]:
    """Load raw per-tribunal NDJSON into DuckDB, produce all 9 tables via Ibis.

    The only raw SQL is ``read_json_auto`` (DuckDB-specific loader).  Everything
    else — UUIDs, name normalization, unnesting, deduplication — is expressed
    as Ibis table expressions executed by the DuckDB backend.
    """
    # One raw SQL call: read_json_auto with filename for tribunal derivation.
    con.raw_sql(
        f"CREATE OR REPLACE TABLE _staging AS "
        f"SELECT * FROM read_json_auto('{ndjson_dir}/*.ndjson', "
        f"filename=true, union_by_name=true)",
    )
    staging = con.table("_staging")

    # Derive _tribunal from filename and add item_id — pure Ibis, no Python loop.
    raw_expr = staging.mutate(
        src_tribunal=staging.filename.split("/")[-1].split(".")[0],
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
            logger.info("table_populated", table=table_name, rows=row_count)

    # Clean up staging tables
    con.drop_table("raw_records", force=True)
    con.drop_table("_staging", force=True)
    return counts


# Explicit Schema Definitions using Ibis
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
    # Process activity index: one row per communication event, NOT a dimension table.
    # For a true process dimension (first/last seen, court unit), build a materialized view.
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
    # Outcome classification per unique text, decoupled from comunicacoes.
    # Composite key: (texto_id, metodo)
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
    # Party dimension table with normalized keys for entity resolution.
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


def upload_to_ia(item_id: str, file_path: Path) -> bool:
    """Upload file to Internet Archive using IA CLI."""
    try:
        logger.info("uploading_to_ia", item_id=item_id, file=file_path.name)
        cmd = ["ia", "upload", item_id, str(file_path), "--metadata", "mediatype:data"]
        # In a real environment, we'd ensure IAS3 keys are set
        # This assumes the environment is already configured or keys are in ~/.ia
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.returncode == 0
    except Exception as e:
        logger.error("upload_failed", item_id=item_id, file=file_path.name, error=str(e))
        return False


def _needs_consolidation(date_str: str, *, must_be_complete: bool = False) -> bool:
    """Check whether *date_str* has collected ZIPs but no consolidated parquets or marker on IA.

    If *must_be_complete* is True, also verifies that all expected tribunals are present.
    """
    item_id = f"djen-{date_str}"
    url = f"https://archive.org/metadata/{item_id}"
    try:
        resp = httpx.get(url, timeout=30)
        if resp.status_code != 200:
            return False
        files = resp.json().get("files", [])
        has_zips = False
        has_consolidated = False
        present_tribunais = set()

        for f in files:
            if not isinstance(f, dict):
                continue
            name = f.get("name", "")
            # Check for ZIPs or absent markers as proof of attempted collection
            if name.endswith((".zip", ".absent")):
                has_zips = True
                # Identify tribunal from filename
                parts = name.replace(".zip", "").replace(".absent", "").split("-")
                if len(parts) >= 4:
                    present_tribunais.add(parts[-1])

            # Check for any .parquet file or the sentinel marker as proof of consolidation
            if name.endswith(".parquet") or name == "_consolidated.marker":
                has_consolidated = True

        if not (has_zips and not has_consolidated):
            return False

        if must_be_complete:
            return len(present_tribunais) >= len(TRIBUNAIS)

        return True
    except Exception:
        return False


def find_next_unconsolidated(max_depth: int = 365) -> str | None:
    """Walk backward from today to find the most recent date needing consolidation.

    Checks d-0, d-1, d-2, … (skipping weekends) until it finds a date that
    has ZIPs on Internet Archive but no consolidated parquets.
    Returns the date string or None if everything is consolidated.
    """
    today = date.today()
    for days_ago in range(max_depth + 1):
        d = today - timedelta(days=days_ago)
        if d.weekday() >= 5:  # skip weekends
            continue
        d_str = d.strftime("%Y-%m-%d")
        # Backfill requires completeness — only consolidate when everything is gathered
        if _needs_consolidation(d_str, must_be_complete=True):
            logger.info("unconsolidated_date_found", date=d_str, days_ago=days_ago)
            return d_str
    return None


def _export_and_upload_table(
    table_name: str,
    con: ibis.BaseBackend,
    output_dir: Path,
    item_id: str,
    *,
    dry_run: bool,
) -> tuple[bool, int]:
    """Export single table to Parquet and upload. Returns (success, parquets_created)."""
    try:
        t = con.table(table_name)
        count = t.count().to_pandas()
        if count == 0:
            return False, 0

        output_path = output_dir / f"{table_name}.parquet"
        con.raw_sql(
            f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD)",
        )
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(
            "parquet_created",
            table=table_name,
            rows=count,
            size_mb=f"{size_mb:.1f}",
        )

        # Upload if not dry run
        uploaded = 0
        if not dry_run and upload_to_ia(item_id, output_path):
            uploaded = 1
            logger.info("uploaded", table=table_name)

        return True, uploaded
    except Exception as e:
        logger.error("parquet_export_failed", table=table_name, error=str(e))
        return False, 0


def consolidate_date(
    date: str,
    *,
    dry_run: bool = False,
    force: bool = False,
    local_zips: str | None = None,
    max_zips: int = 0,
) -> dict[str, int]:
    """Consolidate all tribunals for a date into single Parquet files.

    Args:
        date: Date string in YYYY-MM-DD format.
        dry_run: If True, skip uploading to Internet Archive.
        force: If True, consolidate even if the day is incomplete.
        local_zips: Local directory containing ZIPs (for testing).
        max_zips: Maximum ZIPs to process (0 = unlimited).
    """
    stats = {"zips_processed": 0, "records": 0, "parquets_created": 0, "uploaded": 0}
    item_id = f"djen-{date}"

    # Find all ZIPs and check if day's matrix is complete
    if local_zips:
        zips, present_count = list_local_zips(local_zips)
        logger.info("using_local_zips", directory=local_zips, count=len(zips))
    else:
        zips, present_count = list_zips_for_date(date)

    # Limit ZIPs if max_zips specified (for backfill batching)
    if max_zips > 0 and len(zips) > max_zips:
        logger.info("limiting_zips", total=len(zips), max_zips=max_zips)
        zips = zips[:max_zips]

    expected_count = len(TRIBUNAIS)
    if not force and present_count < expected_count:
        logger.warning(
            "day_not_complete_skipping",
            date=date,
            present=present_count,
            expected=expected_count,
            missing=expected_count - present_count,
        )
        return stats

    if not zips:
        logger.info("nothing_to_consolidate", date=date)
        return stats

    # Use Ibis with DuckDB backend
    con = ibis.duckdb.connect()
    init_tables(con)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        ndjson_dir = tmp_path / "ndjson"
        ndjson_dir.mkdir()

        # Phase 1: Extract ZIPs → raw per-tribunal NDJSON (zero Python mutation)
        ndjson_handles: dict[str, Any] = {}
        try:
            for i, zip_entry in enumerate(zips):
                zip_info: dict[str, Any] = zip_entry
                filename = str(zip_info["filename"])
                tribunal = str(zip_info["tribunal"])

                logger.info(
                    "processing_zip",
                    filename=filename,
                    tribunal=tribunal,
                    progress=f"{i + 1}/{len(zips)}",
                )

                # Download or use local ZIP
                zip_path = tmp_path / filename
                if local_zips and "local_path" in zip_info:
                    import shutil

                    try:
                        shutil.copy2(zip_info["local_path"], zip_path)
                    except Exception as e:
                        logger.warning("local_copy_failed", filename=filename, error=str(e))
                        continue
                elif not download_zip(item_id, filename, zip_path):
                    logger.warning("download_failed", filename=filename)
                    continue

                # Extract JSON from ZIP
                records = extract_json_from_zip(zip_path)
                if not records:
                    logger.warning("no_records_found", filename=filename)
                    zip_path.unlink()
                    continue

                # Stream raw records — one NDJSON per tribunal.
                # Tribunal is derived from the filename in DuckDB, not mutated here.
                if tribunal not in ndjson_handles:
                    ndjson_handles[tribunal] = (ndjson_dir / f"{tribunal}.ndjson").open("w")
                f = ndjson_handles[tribunal]
                for rec in records:
                    if isinstance(rec, dict):
                        f.write(json.dumps(rec, default=str) + "\n")

                stats["zips_processed"] += 1
                stats["records"] += len(records)
                zip_path.unlink()
        finally:
            for fh in ndjson_handles.values():
                fh.close()

        # Phase 2: Ibis-driven transformation (UDFs, unnest, distinct)
        if stats["records"] > 0:
            table_counts = _load_and_transform(con, ndjson_dir, item_id)
            logger.info("transform_complete", tables=table_counts)

        # Phase 3: Export to Parquet and upload
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        logger.info("exporting_parquets", table_count=len(TABLES))

        for table_name in TABLES:
            success, uploaded = _export_and_upload_table(
                table_name,
                con,
                output_dir,
                item_id,
                dry_run=dry_run,
            )
            if success:
                stats["parquets_created"] += 1
                stats["uploaded"] += uploaded

    return stats


def _print_stats(stats: dict[str, int]) -> None:
    print()
    print("=" * 40)
    print("CONSOLIDATION SUMMARY")
    print("=" * 40)
    print(f"  ZIPs processed:   {stats['zips_processed']}")
    print(f"  Records:          {stats['records']}")
    print(f"  Parquets created: {stats['parquets_created']}")
    print(f"  Uploaded:         {stats['uploaded']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolidate DJEN ZIPs to daily Parquets")
    parser.add_argument("--date", help="Date to consolidate (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Don't upload to IA")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Consolidate even if day is not complete",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Find the most recent unconsolidated date (d-1 first) and process it",
    )
    parser.add_argument(
        "--max-zips",
        type=int,
        default=0,
        help="Maximum ZIPs to process per run (0 = unlimited, for backfill)",
    )
    parser.add_argument(
        "--local-zips",
        help="Use local ZIPs from directory instead of downloading from IA (for testing)",
    )
    parser.add_argument(
        "--deadline",
        help="Exit after this duration (e.g., 10m, 600s)",
        default="10m",
    )
    args = parser.parse_args()

    if args.date:
        # Explicit date — existing behaviour
        target_date = args.date
        use_force = args.force
    elif args.backfill:
        # Backfill: walk d-0 → d-1 → d-2 … until we find work
        print("Backfill mode: scanning for unconsolidated dates (d-1 priority)...")
        target_date_or_none = find_next_unconsolidated()
        if target_date_or_none is None:
            print("All dates are already consolidated (or incomplete). Nothing to do.")
            return 0
        target_date = target_date_or_none
        # No more auto-forcing historical dates. We only process them if complete.
        use_force = args.force
    else:
        # Default: today
        target_date = date.today().strftime("%Y-%m-%d")
        use_force = args.force

    print(f"Consolidating DJEN data for {target_date}...")
    print(f"Schema version: {SCHEMA_VERSION}")
    if use_force:
        print("(FORCE mode — will consolidate even if day is incomplete)")
    if args.dry_run:
        print("(DRY RUN — will not upload)")
    print()

    try:
        stats = consolidate_date(
            target_date,
            dry_run=args.dry_run,
            force=use_force,
            local_zips=args.local_zips,
            max_zips=args.max_zips,
        )
    except Exception as e:
        logger.error("consolidation_aborted", error=str(e))
        import traceback

        traceback.print_exc()
        return 1

    _print_stats(stats)

    # Set GitHub Actions output: did we add any files?
    files_added = stats["parquets_created"] > 0
    print(f"\n  Files added: {files_added}")

    # Output for GitHub Actions conditional triggers
    if os_env := os.getenv("GITHUB_OUTPUT"):
        with Path(os_env).open("a") as f:
            f.write(f"files_added={'true' if files_added else 'false'}\n")

    return 0


if __name__ == "__main__":
    exit(main())
