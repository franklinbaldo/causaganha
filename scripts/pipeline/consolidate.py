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
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
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
        zips.append({
            "filename": zip_file.name,
            "tribunal": tribunal,
            "item_id": "local-test",
            "size": zip_file.stat().st_size,
            "local_path": str(zip_file),
        })

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


def _str(val: Any) -> str:
    """Safe string conversion."""
    if val is None:
        return ""
    return str(val).strip()


def _parse_date(val: Any) -> date | None:
    """Parse a date string (YYYY-MM-DD or ISO-8601) to a date object."""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        # Handle both "2026-01-15" and "2026-01-15T00:00:00"
        return date.fromisoformat(s[:10])
    except (ValueError, IndexError):
        return None


def _normalize_name(name: str) -> str:
    """Normalize a party name for deduplication.

    Strips accents, uppercases, collapses whitespace, removes trailing
    punctuation artefacts.
    """
    # NFKD decomposition → strip combining marks (accents)
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Uppercase + collapse whitespace
    return " ".join(s.upper().split())


def _uuid5(data: dict[str, Any]) -> str:
    """Generate deterministic UUIDv5 from dictionary."""
    canonical = json.dumps(data, sort_keys=True)
    return str(uuid.uuid5(NAMESPACE_DJEN, canonical))


def parse_records(
    records: list[dict[str, Any]],
    tribunal: str,
    item_id: str,
) -> dict[str, list[dict[str, Any]]]:
    """Parse JSON records into structured tables based on official DJEN schema."""
    tables: dict[str, list[dict[str, Any]]] = {
        "comunicacoes": [],
        "advogados": [],
        "advogado_nomes": [],
        "destinatarios": [],
        "comunicacao_advogados": [],
        "textos": [],
        "representacoes": [],
        "processos": [],
        "partes": [],
    }

    processed_at = datetime.now()

    for record in records:
        if not isinstance(record, dict):
            continue

        # Generate deterministic UUIDv5 for the communication
        # Includes tribunal to ensure uniqueness across sources
        com_id = _uuid5({**record, "tribunal": tribunal})
        orig_com_id = _str(record.get("id"))
        tribunal_s = _str(tribunal)

        # Parse the availability date once
        data_disp = _parse_date(
            record.get("data_disponibilizacao") or record.get("dataDisponibilizacao"),
        )

        # Text deduplication via UUIDv5 of content
        texto_content = record.get("texto")
        texto_id = ""
        if texto_content:
            texto_s = _str(texto_content)
            texto_id = _uuid5({"texto": texto_s})
            tables["textos"].append(
                {
                    "id": texto_id,
                    "texto": texto_s,
                },
            )

        # Partition keys
        p_ano = data_disp.year if data_disp else 0
        p_mes = data_disp.month if data_disp else 0

        # Main communication record
        tables["comunicacoes"].append(
            {
                "id": com_id,
                "original_id": orig_com_id,
                "tribunal": tribunal_s,
                "numero_processo": _str(
                    record.get("numero_processo") or record.get("numeroProcesso"),
                ),
                "numero_processo_mascara": _str(record.get("numeroprocessocommascara")),
                "data_disponibilizacao": data_disp,
                "tipo_comunicacao": _str(record.get("tipoComunicacao")),
                "nome_orgao": _str(record.get("nomeOrgao") or record.get("orgao")),
                "meio": _str(record.get("meio")),
                "link": _str(record.get("link")),
                "tipo_documento": _str(record.get("tipoDocumento")),
                "nome_classe": _str(record.get("nomeClasse")),
                "codigo_classe": _str(record.get("codigoClasse")),
                "numero_comunicacao": _str(record.get("numeroComunicacao")),
                "hash": _str(record.get("hash")),
                "processed_at": processed_at,
                "texto_id": texto_id,
                "p_ano": p_ano,
                "p_mes": p_mes,
                "p_item_ia": item_id,
            },
        )

        # Destinatarios (Parties) — also populate partes dimension
        current_destinatarios = []
        for dest in record.get("destinatarios") or []:
            if isinstance(dest, dict):
                p_nome = _str(dest.get("nome"))
                p_polo = _str(dest.get("polo"))

                # Generate normalized party ID
                nome_norm = _normalize_name(p_nome) if p_nome else ""
                parte_id = _uuid5({"nome_normalizado": nome_norm}) if nome_norm else ""

                if parte_id:
                    tables["partes"].append(
                        {
                            "id": parte_id,
                            "nome_normalizado": nome_norm,
                            "nome_original": p_nome,
                        },
                    )

                dest_data = {
                    "comunicacao_id": com_id,
                    "tribunal": tribunal_s,
                    "nome": p_nome,
                    "polo": p_polo,
                    "parte_id": parte_id,
                    "p_ano": p_ano,
                    "p_mes": p_mes,
                    "p_item_ia": item_id,
                }
                tables["destinatarios"].append(dest_data)
                current_destinatarios.append(
                    {"nome": p_nome, "polo": p_polo, "parte_id": parte_id},
                )

        # Advogados (via destinatarioadvogados)
        for dest_adv in record.get("destinatarioadvogados") or []:
            if isinstance(dest_adv, dict):
                adv = dest_adv.get("advogado") or {}
                orig_adv_id = _str(adv.get("id") or dest_adv.get("advogado_id"))

                # Global Lawyer ID: Deterministic across tribunals
                # Based on OAB + UF only (name is a mutable attribute)
                adv_nome = _str(adv.get("nome"))
                adv_oab = _str(adv.get("numero_oab") or adv.get("numeroOAB"))
                adv_uf = _str(adv.get("uf_oab") or adv.get("ufOAB"))

                # If we have OAB/UF, use them for a stable key
                # Otherwise fallback to Name + Tribunal (less stable but safe)
                if adv_oab and adv_uf:
                    adv_global_id = _uuid5({"oab": adv_oab, "uf": adv_uf})
                else:
                    adv_global_id = _uuid5(
                        {"nome": adv_nome, "tribunal": tribunal_s, "orig_id": orig_adv_id},
                    )

                tables["comunicacao_advogados"].append(
                    {
                        "comunicacao_id": com_id,
                        "tribunal": tribunal_s,
                        "advogado_id": adv_global_id,
                    },
                )

                if adv:
                    tables["advogados"].append(
                        {
                            "id": adv_global_id,
                            "original_id": orig_adv_id,
                            "tribunal": tribunal_s,
                            "nome": adv_nome,
                            "numero_oab": adv_oab,
                            "uf_oab": adv_uf,
                            "p_ano": p_ano,
                            "p_mes": p_mes,
                            "p_item_ia": item_id,
                        },
                    )

                    # Track name aliases for this lawyer
                    tables["advogado_nomes"].append(
                        {
                            "advogado_id": adv_global_id,
                            "nome": adv_nome,
                            "tribunal": tribunal_s,
                            "first_seen": data_disp,
                        },
                    )

                    # Create explicit representation mapping (Lawyer -> Party)
                    for party in current_destinatarios:
                        tables["representacoes"].append(
                            {
                                "comunicacao_id": com_id,
                                "tribunal": tribunal_s,
                                "advogado_id": adv_global_id,
                                "parte_id": party["parte_id"],
                                "polo": party["polo"],
                                "p_ano": p_ano,
                                "p_mes": p_mes,
                                "p_item_ia": item_id,
                            },
                        )

        # Process activity index — one row per communication event
        tables["processos"].append(
            {
                "numero_processo": _str(
                    record.get("numero_processo") or record.get("numeroProcesso"),
                ),
                "tribunal": tribunal_s,
                "data": data_disp,
                "comunicacao_id": com_id,
                "p_ano": p_ano,
                "p_mes": p_mes,
                "p_item_ia": item_id,
            },
        )

    return tables


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


def consolidate_date(date: str, *, dry_run: bool = False, force: bool = False, local_zips: str | None = None) -> dict[str, int]:
    """Consolidate all tribunals for a date into single Parquet files."""
    stats = {"zips_processed": 0, "records": 0, "parquets_created": 0, "uploaded": 0}
    item_id = f"djen-{date}"

    # Find all ZIPs and check if day's matrix is complete
    if local_zips:
        zips, present_count = list_local_zips(local_zips)
        logger.info("using_local_zips", directory=local_zips, count=len(zips))
    else:
        zips, present_count = list_zips_for_date(date)

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
                # Copy from local directory
                import shutil
                try:
                    shutil.copy2(zip_info["local_path"], zip_path)
                except Exception as e:
                    logger.warning("local_copy_failed", filename=filename, error=str(e))
                    continue
            else:
                # Download from IA
                if not download_zip(item_id, filename, zip_path):
                    logger.warning("download_failed", filename=filename)
                    continue

            # Extract and parse JSON
            records = extract_json_from_zip(zip_path)
            if not records:
                logger.warning("no_records_found", filename=filename)
                zip_path.unlink()
                continue

            # Parse into tables
            tables = parse_records(records, tribunal, item_id)

            # Insert into DuckDB immediately to free Python memory
            for table_name, rows in tables.items():
                if rows:
                    # Use ibis memtable with explicit schema for validation
                    data = ibis.memtable(rows, schema=TABLE_SCHEMAS[table_name])
                    con.insert(table_name, data)

            stats["zips_processed"] += 1
            stats["records"] += len(records)

            # Clean up to save disk space
            zip_path.unlink()

        # Write consolidated Parquet files (PARALLEL)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        logger.info("exporting_parquets", table_count=len(TABLES), concurrent_workers=3)

        # Export tables in parallel (2-3 concurrent workers)
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(_export_and_upload_table, table_name, con, output_dir, item_id, dry_run)
                for table_name in TABLES
            ]
            for future in futures:
                success, uploaded = future.result()
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
        "--local-zips",
        help="Use local ZIPs from directory instead of downloading from IA (for testing)",
    )
    parser.add_argument("--deadline", help="Exit after this duration (e.g., 10m, 600s)", default="10m")
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
        stats = consolidate_date(target_date, dry_run=args.dry_run, force=use_force, local_zips=args.local_zips)
    except Exception as e:
        logger.error("consolidation_aborted", error=str(e))
        import traceback

        traceback.print_exc()
        return 1

    _print_stats(stats)

    # Set GitHub Actions output: did we add any files?
    files_added = stats['parquets_created'] > 0
    print(f"\n  Files added: {files_added}")

    # Output for GitHub Actions conditional triggers
    if os_env := os.getenv("GITHUB_OUTPUT"):
        with open(os_env, "a") as f:
            f.write(f"files_added={'true' if files_added else 'false'}\n")

    return 0 if stats["parquets_created"] > 0 else 1


if __name__ == "__main__":
    exit(main())
