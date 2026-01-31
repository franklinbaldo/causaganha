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


# Schema version — embedded in Parquet metadata for forward compatibility.
# Bump when TABLE_SCHEMAS change in a way that affects consumers.
# v3: Added p_ano, p_mes, p_item_ia columns for better partitioning and tracing.
SCHEMA_VERSION = "3"


logger = structlog.get_logger()

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


def _register_udfs(con: ibis.BaseBackend) -> None:
    """Register Python scalar UDFs for computations DuckDB cannot do natively.

    Only uuid5 requires Python — name normalization uses DuckDB's built-in
    strip_accents() + UPPER() + REGEXP_REPLACE().
    """
    import duckdb

    namespace = NAMESPACE_DJEN

    def djen_uuid5(s: str) -> str | None:
        if s is None:
            return None
        return str(uuid.uuid5(namespace, s))

    con.con.create_function(
        "djen_uuid5",
        djen_uuid5,
        [duckdb.typing.VARCHAR],
        duckdb.typing.VARCHAR,
    )


# ---------------------------------------------------------------------------
# SQL building blocks
# ---------------------------------------------------------------------------
# Reusable SQL fragments to avoid repetition in table templates.

# Parse date from either snake_case or camelCase DJEN field
_SQL_DATE = """TRY_CAST(LEFT(COALESCE(
    CAST(COALESCE(r.data_disponibilizacao, r.dataDisponibilizacao) AS VARCHAR),
    ''), 10) AS DATE)"""

# Partition columns derived from the date
_SQL_P_ANO = f"COALESCE(YEAR({_SQL_DATE}), 0)"
_SQL_P_MES = f"COALESCE(MONTH({_SQL_DATE}), 0)"

# Communication UUID: hash of DJEN original id + tribunal
_SQL_COM_ID = "djen_uuid5(COALESCE(CAST(r.id AS VARCHAR), '') || ':' || r._tribunal)"

# Text UUID: content-addressed hash of the text itself
_SQL_TEXTO_ID = "djen_uuid5(COALESCE(TRIM(CAST(r.texto AS VARCHAR)), ''))"

# Name normalization: strip accents, uppercase, collapse whitespace (pure SQL)
_SQL_NORMALIZE = (
    "UPPER(TRIM(REGEXP_REPLACE(strip_accents("
    "COALESCE(CAST({field} AS VARCHAR), '')"
    "), '\\s+', ' ', 'g')))"
)

# Party UUID: hash of normalized name
_SQL_PARTE_ID = f"djen_uuid5({_SQL_NORMALIZE.format(field='d.nome')})"

# Advogado UUID: prefer OAB+UF key, fall back to nome+tribunal+orig_id
_SQL_OAB = (
    "COALESCE(TRIM(CAST(COALESCE(da.advogado.numero_oab, da.advogado.numeroOAB) AS VARCHAR)), '')"
)
_SQL_UF = "COALESCE(TRIM(CAST(COALESCE(da.advogado.uf_oab, da.advogado.ufOAB) AS VARCHAR)), '')"
_SQL_ADV_GLOBAL_ID = f"""CASE
    WHEN {_SQL_OAB} != '' AND {_SQL_UF} != ''
    THEN djen_uuid5({_SQL_OAB} || ':' || {_SQL_UF})
    ELSE djen_uuid5(
        COALESCE(TRIM(CAST(da.advogado.nome AS VARCHAR)), '') || ':' ||
        r._tribunal || ':' ||
        COALESCE(TRIM(CAST(COALESCE(da.advogado.id, da.advogado_id) AS VARCHAR)), ''))
END"""

# ---------------------------------------------------------------------------
# SQL templates — all transformation happens here, no Python loops needed.
# DuckDB UNNEST replaces the old parse_records() triple-nested Python loops.
# UUIDs are computed inline via the djen_uuid5() scalar UDF.
# ---------------------------------------------------------------------------

_SQL_COMUNICACOES = f"""
INSERT INTO comunicacoes
SELECT
    {_SQL_COM_ID}                                                    AS id,
    COALESCE(TRIM(CAST(r.id AS VARCHAR)), '')                        AS original_id,
    r._tribunal                                                      AS tribunal,
    COALESCE(TRIM(CAST(COALESCE(r.numero_processo, r.numeroProcesso) AS VARCHAR)), '')
                                                                     AS numero_processo,
    COALESCE(TRIM(CAST(r.numeroprocessocommascara AS VARCHAR)), '')   AS numero_processo_mascara,
    {_SQL_DATE}                                                      AS data_disponibilizacao,
    COALESCE(TRIM(CAST(r.tipoComunicacao AS VARCHAR)), '')            AS tipo_comunicacao,
    COALESCE(TRIM(CAST(COALESCE(r.nomeOrgao, r.orgao) AS VARCHAR)), '')
                                                                     AS nome_orgao,
    COALESCE(TRIM(CAST(r.meio AS VARCHAR)), '')                       AS meio,
    COALESCE(TRIM(CAST(r.link AS VARCHAR)), '')                       AS link,
    COALESCE(TRIM(CAST(r.tipoDocumento AS VARCHAR)), '')              AS tipo_documento,
    COALESCE(TRIM(CAST(r.nomeClasse AS VARCHAR)), '')                 AS nome_classe,
    COALESCE(TRIM(CAST(r.codigoClasse AS VARCHAR)), '')               AS codigo_classe,
    COALESCE(TRIM(CAST(r.numeroComunicacao AS VARCHAR)), '')          AS numero_comunicacao,
    COALESCE(TRIM(CAST(r.hash AS VARCHAR)), '')                       AS hash,
    CURRENT_TIMESTAMP                                                 AS processed_at,
    CASE WHEN r.texto IS NOT NULL AND TRIM(CAST(r.texto AS VARCHAR)) != ''
         THEN {_SQL_TEXTO_ID} ELSE '' END                            AS texto_id,
    {_SQL_P_ANO}                                                     AS p_ano,
    {_SQL_P_MES}                                                     AS p_mes,
    r._item_id                                                        AS p_item_ia
FROM raw_records r
"""

_SQL_TEXTOS = f"""
INSERT INTO textos
SELECT DISTINCT
    {_SQL_TEXTO_ID}                              AS id,
    COALESCE(TRIM(CAST(r.texto AS VARCHAR)), '') AS texto
FROM raw_records r
WHERE r.texto IS NOT NULL AND TRIM(CAST(r.texto AS VARCHAR)) != ''
"""

_SQL_DESTINATARIOS = f"""
INSERT INTO destinatarios
SELECT
    {_SQL_COM_ID}                                                   AS comunicacao_id,
    r._tribunal                                                     AS tribunal,
    COALESCE(TRIM(CAST(d.nome AS VARCHAR)), '')                     AS nome,
    COALESCE(TRIM(CAST(d.polo AS VARCHAR)), '')                     AS polo,
    {_SQL_PARTE_ID}                                                 AS parte_id,
    {_SQL_P_ANO}                                                    AS p_ano,
    {_SQL_P_MES}                                                    AS p_mes,
    r._item_id                                                      AS p_item_ia
FROM raw_records r, UNNEST(r.destinatarios) AS t(d)
"""

_SQL_PARTES = f"""
INSERT INTO partes
SELECT DISTINCT ON (parte_id)
    {_SQL_PARTE_ID}                                                 AS parte_id,
    {_SQL_NORMALIZE.format(field="d.nome")}                         AS nome_normalizado,
    COALESCE(TRIM(CAST(d.nome AS VARCHAR)), '')                     AS nome_original
FROM raw_records r, UNNEST(r.destinatarios) AS t(d)
WHERE {_SQL_NORMALIZE.format(field="d.nome")} != ''
"""

_SQL_COMUNICACAO_ADVOGADOS = f"""
INSERT INTO comunicacao_advogados
SELECT
    {_SQL_COM_ID}                                                   AS comunicacao_id,
    r._tribunal                                                     AS tribunal,
    {_SQL_ADV_GLOBAL_ID}                                            AS advogado_id
FROM raw_records r, UNNEST(r.destinatarioadvogados) AS t(da)
"""

_SQL_ADVOGADOS = f"""
INSERT INTO advogados
SELECT
    {_SQL_ADV_GLOBAL_ID}                                            AS id,
    COALESCE(TRIM(CAST(COALESCE(da.advogado.id, da.advogado_id) AS VARCHAR)), '')
                                                                    AS original_id,
    r._tribunal                                                     AS tribunal,
    COALESCE(TRIM(CAST(da.advogado.nome AS VARCHAR)), '')           AS nome,
    {_SQL_OAB}                                                      AS numero_oab,
    {_SQL_UF}                                                       AS uf_oab,
    {_SQL_P_ANO}                                                    AS p_ano,
    {_SQL_P_MES}                                                    AS p_mes,
    r._item_id                                                      AS p_item_ia
FROM raw_records r, UNNEST(r.destinatarioadvogados) AS t(da)
WHERE da.advogado IS NOT NULL
"""

_SQL_ADVOGADO_NOMES = f"""
INSERT INTO advogado_nomes
SELECT
    {_SQL_ADV_GLOBAL_ID}                                            AS advogado_id,
    COALESCE(TRIM(CAST(da.advogado.nome AS VARCHAR)), '')           AS nome,
    r._tribunal                                                     AS tribunal,
    {_SQL_DATE}                                                     AS first_seen
FROM raw_records r, UNNEST(r.destinatarioadvogados) AS t(da)
WHERE da.advogado IS NOT NULL
"""

_SQL_REPRESENTACOES = f"""
INSERT INTO representacoes
SELECT
    {_SQL_COM_ID}                                                   AS comunicacao_id,
    r._tribunal                                                     AS tribunal,
    {_SQL_ADV_GLOBAL_ID}                                            AS advogado_id,
    {_SQL_PARTE_ID}                                                 AS parte_id,
    COALESCE(TRIM(CAST(d.polo AS VARCHAR)), '')                     AS polo,
    {_SQL_P_ANO}                                                    AS p_ano,
    {_SQL_P_MES}                                                    AS p_mes,
    r._item_id                                                      AS p_item_ia
FROM raw_records r,
     UNNEST(r.destinatarios) AS t1(d),
     UNNEST(r.destinatarioadvogados) AS t2(da)
WHERE da.advogado IS NOT NULL
"""

_SQL_PROCESSOS = f"""
INSERT INTO processos
SELECT
    COALESCE(TRIM(CAST(COALESCE(r.numero_processo, r.numeroProcesso) AS VARCHAR)), '')
                                                                    AS numero_processo,
    r._tribunal                                                     AS tribunal,
    {_SQL_DATE}                                                     AS data,
    {_SQL_COM_ID}                                                   AS comunicacao_id,
    {_SQL_P_ANO}                                                    AS p_ano,
    {_SQL_P_MES}                                                    AS p_mes,
    r._item_id                                                      AS p_item_ia
FROM raw_records r
"""

# Ordered list: tables with foreign-key dependencies come after their parents.
_TABLE_SQL: tuple[tuple[str, str], ...] = (
    ("comunicacoes", _SQL_COMUNICACOES),
    ("textos", _SQL_TEXTOS),
    ("destinatarios", _SQL_DESTINATARIOS),
    ("partes", _SQL_PARTES),
    ("comunicacao_advogados", _SQL_COMUNICACAO_ADVOGADOS),
    ("advogados", _SQL_ADVOGADOS),
    ("advogado_nomes", _SQL_ADVOGADO_NOMES),
    ("representacoes", _SQL_REPRESENTACOES),
    ("processos", _SQL_PROCESSOS),
)


def _load_and_transform(
    con: ibis.BaseBackend,
    ndjson_path: Path,
) -> dict[str, int]:
    """Load raw NDJSON into DuckDB and produce all 9 tables via UNNEST + UDFs.

    All transformation — UUIDs, name normalization, flattening, deduplication —
    happens in SQL.  Python is only involved as a scalar UDF for uuid5.
    Returns row counts per table.
    """
    duck = con.con

    # Register the uuid5 UDF so SQL templates can call djen_uuid5()
    _register_udfs(con)

    # Load raw records (only _tribunal/_item_id added, no Python enrichment)
    duck.execute(
        f"CREATE OR REPLACE TABLE raw_records AS SELECT * FROM read_json_auto('{ndjson_path}')",
    )

    counts: dict[str, int] = {}
    for table_name, sql in _TABLE_SQL:
        duck.execute(sql)
        row_count = duck.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        counts[table_name] = row_count
        if row_count:
            logger.info("table_populated", table=table_name, rows=row_count)

    # Clean up raw staging table
    duck.execute("DROP TABLE IF EXISTS raw_records")
    return counts


# Explicit Schema Definitions using Ibis
NAMESPACE_DJEN = uuid.uuid5(uuid.NAMESPACE_DNS, "djen.causaganha.org")

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
        ndjson_path = tmp_path / "enriched.ndjson"

        # Phase 1: Extract ZIPs, enrich with UUIDs, write to NDJSON
        with ndjson_path.open("w") as ndjson_f:
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

                # Stream raw records to NDJSON — only add routing metadata.
                # All UUIDs, normalization, and flattening happen in DuckDB SQL.
                for rec in records:
                    if not isinstance(rec, dict):
                        continue
                    rec["_tribunal"] = tribunal
                    rec["_item_id"] = item_id
                    ndjson_f.write(json.dumps(rec, default=str) + "\n")

                stats["zips_processed"] += 1
                stats["records"] += len(records)
                zip_path.unlink()

        # Phase 2: DuckDB vectorized transformation (UNNEST, DISTINCT, cross-join)
        if stats["records"] > 0:
            table_counts = _load_and_transform(con, ndjson_path)
            logger.info("vectorized_transform_complete", tables=table_counts)

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

    return 0 if stats["parquets_created"] > 0 else 1


if __name__ == "__main__":
    exit(main())
