#!/usr/bin/env python3

MAGIC_VAL_4 = 4

"""Convert DJEN ZIP files to Parquet format.

This script downloads ZIP files from Internet Archive, converts them to
Parquet format, and uploads the Parquet files back to IA.

Usage:
    # Convert recent files (finds ZIPs without corresponding Parquets)
    python scripts/pipeline/convert.py

    # Convert specific date
    python scripts/pipeline/convert.py --date 2026-01-27

    # Limit number of items
    python scripts/pipeline/convert.py --max-items 10
"""

import argparse
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import duckdb
import structlog

from causaganha.storage.djen_schema import (
    FIELD_DATA_DISPONIBILIZACAO,
    FIELD_NOME_ORGAO,
    FIELD_NUMERO_OAB,
    FIELD_NUMERO_PROCESSO,
    FIELD_SIGLA_TRIBUNAL,
    FIELD_UF_OAB,
    get_field,
)


logger = structlog.get_logger()


def get_unconverted_zips() -> list[dict]:
    """Find ZIP files on IA that don't have corresponding Parquet files."""
    logger.info("finding_unconverted_zips")
    zips = {}
    parquets = set()

    try:
        # List all djen-* items
        result = subprocess.run(
            ["ia", "search", "identifier:djen-*", "--itemlist"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            return []

        items = [line.strip() for line in result.stdout.splitlines() if line.strip()]

        for item_id in items:
            if item_id == "causaganha-catalog":
                continue

            try:
                list_result = subprocess.run(
                    ["ia", "list", item_id, "--glob", "*.{zip,parquet}"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if list_result.returncode == 0:
                    for filename in list_result.stdout.splitlines():
                        filename = filename.strip()
                        if filename.endswith(".zip"):
                            # djen-2026-01-27-TJSP.zip
                            zips[filename] = item_id
                        elif filename.endswith(".parquet"):
                            # djen-2026-01-27-TJSP-comunicacoes.parquet
                            # Extract base: djen-2026-01-27-TJSP
                            base = "-".join(filename.replace(".parquet", "").split("-")[:-1])
                            parquets.add(base + ".zip")
            except subprocess.TimeoutExpired:
                continue

    except Exception as e:
        logger.warning("search_failed", error=str(e))

    # Find ZIPs without Parquets
    unconverted = []
    for zip_name, item_id in zips.items():
        if zip_name not in parquets:
            unconverted.append({"zip": zip_name, "item_id": item_id})

    logger.info("unconverted_zips_found", count=len(unconverted))
    return unconverted


def download_zip(item_id: str, filename: str, output_path: Path) -> bool:
    """Download ZIP from Internet Archive."""
    url = f"https://archive.org/download/{item_id}/{filename}"
    try:
        result = subprocess.run(
            ["curl", "-sfL", url, "-o", str(output_path)],
            timeout=120,
        )
        return result.returncode == 0 and output_path.exists()
    except Exception as e:
        logger.warning("download_failed", error=str(e))
        return False


def extract_json_from_zip(zip_path: Path) -> list[dict]:
    """Extract and parse JSON data from ZIP file."""
    records = []
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
                            records.append(data)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
    except zipfile.BadZipFile:
        logger.warning("bad_zip_file", path=str(zip_path))
    return records


def convert_to_parquet(records: list[dict], output_dir: Path, base_name: str) -> list[Path]:
    """Convert JSON records to Parquet files."""
    output_files = []

    if not records:
        return output_files

    # Group records by type
    comunicacoes = []
    advogados = []
    partes = []

    for record in records:
        if not isinstance(record, dict):
            continue

        # Main communication record
        comunicacoes.append(
            {
                "id": record.get("id"),
                "numero_processo": get_field(record, FIELD_NUMERO_PROCESSO),
                "data_disponibilizacao": get_field(record, FIELD_DATA_DISPONIBILIZACAO),
                "tribunal": get_field(record, FIELD_SIGLA_TRIBUNAL),
                "orgao": get_field(record, FIELD_NOME_ORGAO),
                "texto": record.get("texto", "")[:10000],  # Limit text size
            },
        )

        # Extract lawyers
        for adv in record.get("advogados", []) or []:
            if isinstance(adv, dict):
                advogados.append(
                    {
                        "comunicacao_id": record.get("id"),
                        "nome": adv.get("nome"),
                        "oab": get_field(adv, FIELD_NUMERO_OAB),
                        "uf_oab": get_field(adv, FIELD_UF_OAB),
                    },
                )

        # Extract parties
        for parte in record.get("partes", []) or []:
            if isinstance(parte, dict):
                partes.append(
                    {
                        "comunicacao_id": record.get("id"),
                        "nome": parte.get("nome"),
                        "tipo": parte.get("tipo"),
                        "polo": parte.get("polo"),
                    },
                )

    # Write Parquet files using DuckDB
    con = duckdb.connect()

    for table_name, data in [
        ("comunicacoes", comunicacoes),
        ("advogados", advogados),
        ("partes", partes),
    ]:
        if not data:
            continue

        output_path = output_dir / f"{base_name}-{table_name}.parquet"

        try:
            # Create table from records
            con.execute("DROP TABLE IF EXISTS temp")
            columns = list(data[0].keys())
            col_defs = ", ".join([f'"{c}" VARCHAR' for c in columns])
            con.execute(f"CREATE TABLE temp ({col_defs})")

            # Insert data
            for row in data:
                values = [str(row.get(c, "")) if row.get(c) is not None else None for c in columns]
                placeholders = ", ".join(["?" for _ in columns])
                con.execute(f"INSERT INTO temp VALUES ({placeholders})", values)

            # Export to Parquet with compression
            con.execute(f"COPY temp TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
            output_files.append(output_path)
            logger.debug("parquet_created", path=str(output_path), rows=len(data))

        except Exception as e:
            logger.warning("parquet_creation_failed", table=table_name, error=str(e))

    con.close()
    return output_files


def upload_parquets(item_id: str, files: list[Path]) -> int:
    """Upload Parquet files to Internet Archive."""
    success = 0
    for file_path in files:
        try:
            result = subprocess.run(
                [
                    "ia",
                    "upload",
                    item_id,
                    str(file_path),
                    "--retries=3",
                    "--no-derive",
                ],
                capture_output=True,
                timeout=120,
            )
            if result.returncode == 0:
                success += 1
        except Exception:
            continue
    return success


def convert_data(target_date: str | None = None, max_items: int = 20) -> dict:
    """Main conversion function."""
    stats = {"converted": 0, "failed": 0, "files_uploaded": 0}

    # Find unconverted ZIPs
    unconverted = get_unconverted_zips()

    # Filter by date if specified
    if target_date:
        unconverted = [u for u in unconverted if target_date in u["zip"]]

    logger.info("items_to_convert", count=len(unconverted), max_items=max_items)

    for item in unconverted[:max_items]:
        zip_name = item["zip"]
        item_id = item["item_id"]
        base_name = zip_name.replace(".zip", "")

        logger.info("converting", zip=zip_name, item_id=item_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            zip_path = tmpdir / zip_name

            # Download ZIP
            if not download_zip(item_id, zip_name, zip_path):
                stats["failed"] += 1
                continue

            # Extract and parse JSON
            records = extract_json_from_zip(zip_path)
            if not records:
                logger.warning("no_records", zip=zip_name)
                stats["failed"] += 1
                continue

            # Convert to Parquet
            parquet_files = convert_to_parquet(records, tmpdir, base_name)
            if not parquet_files:
                stats["failed"] += 1
                continue

            # Upload Parquets to tribunal-year item
            parts = base_name.replace("djen-", "").split("-")
            if len(parts) >= MAGIC_VAL_4:
                date_str = "-".join(parts[:3])
                tribunal = parts[3]
                year = date_str[:4]
                upload_item_id = f"djen-{tribunal.lower()}-{year}"
            else:
                upload_item_id = item_id

            uploaded = upload_parquets(upload_item_id, parquet_files)
            stats["files_uploaded"] += uploaded
            stats["converted"] += 1
            logger.info("converted", zip=zip_name, parquets=len(parquet_files))

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert DJEN ZIPs to Parquet")
    parser.add_argument("--date", help="Specific date (YYYY-MM-DD)")
    parser.add_argument("--max-items", type=int, default=20)
    args = parser.parse_args()

    if args.date:
        pass

    stats = convert_data(target_date=args.date, max_items=args.max_items)

    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
