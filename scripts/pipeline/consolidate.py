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
import json
import subprocess
import tempfile
import time
import unicodedata
import uuid
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx
import ibis
import structlog

from causaganha.config import TRIBUNAIS


# Schema version — embedded in Parquet metadata for forward compatibility.
# Bump when TABLE_SCHEMAS change in a way that affects consumers.
SCHEMA_VERSION = "2"


logger = structlog.get_logger()

# Table types to consolidate - Defined below via TABLE_SCHEMAS


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


def parse_records(records: list[dict[str, Any]], tribunal: str) -> dict[str, list[dict[str, Any]]]:
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


def _needs_consolidation(date_str: str) -> bool:
    """Check whether *date_str* has collected ZIPs but no consolidated parquets on IA."""
    item_id = f"djen-{date_str}"
    url = f"https://archive.org/metadata/{item_id}"
    try:
        resp = httpx.get(url, timeout=30)
        if resp.status_code != 200:
            return False
        files = resp.json().get("files", [])
        has_zips = False
        has_parquets = False
        for f in files:
            if not isinstance(f, dict):
                continue
            name = f.get("name", "")
            if name.endswith((".zip", ".absent")):
                has_zips = True
            if name == "comunicacoes.parquet":
                has_parquets = True
        return has_zips and not has_parquets
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
        if _needs_consolidation(d_str):
            logger.info("unconsolidated_date_found", date=d_str, days_ago=days_ago)
            return d_str
    return None


def consolidate_date(date: str, *, dry_run: bool = False, force: bool = False) -> dict[str, int]:
    """Consolidate all tribunals for a date into single Parquet files."""
    stats = {"zips_processed": 0, "records": 0, "parquets_created": 0, "uploaded": 0}
    item_id = f"djen-{date}"

    # Find all ZIPs and check if day's matrix is complete
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

            # Download ZIP
            zip_path = tmp_path / filename
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
            tables = parse_records(records, tribunal)

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

        # Write consolidated Parquet files
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        for table_name in TABLES:
            t = con.table(table_name)
            count = t.count().to_pandas()  # to_pandas() is used here just for the scalar count
            if count == 0:
                continue

            output_path = output_dir / f"{table_name}.parquet"
            try:
                # Use DuckDB raw export via Ibis for ZSTD compression support
                # Ibis doesn't expose all Parquet options directly in a unified way easily for ZSTD
                con.raw_sql(
                    f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD)",
                )
                stats["parquets_created"] += 1
                size_mb = output_path.stat().st_size / (1024 * 1024)
                logger.info(
                    "parquet_created",
                    table=table_name,
                    rows=count,
                    size_mb=f"{size_mb:.1f}",
                )

                # Upload if not dry run
                if not dry_run and upload_to_ia(item_id, output_path):
                    stats["uploaded"] += 1
                    logger.info("uploaded", table=table_name)
            except Exception as e:
                logger.error("parquet_export_failed", table=table_name, error=str(e))

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
            print("All dates are already consolidated. Nothing to do.")
            return 0
        target_date = target_date_or_none
        # Force-consolidate historical dates — they may never reach 100% tribunal coverage
        today_str = date.today().strftime("%Y-%m-%d")
        use_force = args.force or (target_date != today_str)
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
        stats = consolidate_date(target_date, dry_run=args.dry_run, force=use_force)
    except Exception as e:
        logger.error("consolidation_aborted", error=str(e))
        import traceback

        traceback.print_exc()
        return 1

    _print_stats(stats)
    return 0 if stats["parquets_created"] > 0 else 1


if __name__ == "__main__":
    exit(main())
