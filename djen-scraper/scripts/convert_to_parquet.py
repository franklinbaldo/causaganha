#!/usr/bin/env python3

MAGIC_VAL_2 = 2
HTTP_200_OK = 200

"""Convert DJEN ZIP files from Internet Archive to Parquet tables using DuckDB.

Optimized version:
- Direct HTTP download (faster than ia CLI)
- Stream JSON from ZIP without extracting all files
- Detailed timing for profiling

Usage:
    python convert_to_parquet.py batch.txt
"""

import json

# Parallel processing config (adaptive based on CPU)
import multiprocessing
import os
import sys
import tempfile
import time
import traceback
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import duckdb
import httpx
import internetarchive as ia  # type: ignore


_cpu_count = multiprocessing.cpu_count()
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", str(min(_cpu_count, 4))))

# UUIDv5 namespace for DJEN
NAMESPACE_DJEN = uuid.uuid5(uuid.NAMESPACE_DNS, "djen.jus.br")


def generate_uuid(content: str) -> str:
    """Generate deterministic UUIDv5 from content."""
    return str(uuid.uuid5(NAMESPACE_DJEN, content))


def timed(name: str):
    """Context manager for timing code blocks."""

    class Timer:
        def __init__(self, name) -> None:
            self.name = name

        def __enter__(self):
            self.start = time.time()
            return self

        def __exit__(self, *args):
            self.elapsed = time.time() - self.start

    return Timer(name)


def process_item(entry: str) -> bool:
    """Process a single ZIP file from Internet Archive.

    Args:
        entry: Either "DATE|TRIBUNAL" format or legacy "djen-raw-DATE-TRIBUNAL" item_id
    """
    # Support both new format (DATE|TRIBUNAL) and legacy format (djen-DATE-TRIBUNAL)
    if "|" in entry:
        date, tribunal = entry.split("|", 1)
        item_id = f"djen-{date}"
    else:
        # Legacy format: djen-2026-01-21-TJSP or djen-raw-2026-01-21-TJSP
        entry = entry.replace("djen-raw-", "djen-")
        parts = entry.replace("djen-", "").rsplit("-", 1)
        date = parts[0]
        tribunal = parts[1]
        item_id = f"djen-{date}"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        zip_path = tmpdir / "caderno.zip"  # Placeholder path, will be overwritten

        # Try to download the ZIP file
        # We try multiple patterns for backward compatibility:
        # 1. New pattern: djen-{date}-{tribunal}.zip
        # 2. Old pattern: {tribunal}-{date}.zip
        # 3. Legacy pattern: caderno.zip
        zip_filenames = [f"djen-{date}-{tribunal}.zip", f"{tribunal}-{date}.zip", "caderno.zip"]
        download_success = False

        for zip_filename in zip_filenames:
            url = f"https://archive.org/download/{item_id}/{zip_filename}"

            with timed(f"download ({zip_filename})"):
                # Long timeouts for large files from IA
                timeout = httpx.Timeout(connect=30, read=600, write=30, pool=30)
                with httpx.stream(
                    "GET",
                    url,
                    timeout=timeout,
                    follow_redirects=True,
                ) as response:
                    if response.status_code == HTTP_200_OK:
                        downloaded = 0
                        with Path(zip_path).open("wb") as f:
                            for chunk in response.iter_bytes(
                                chunk_size=1024 * 1024,
                            ):  # 1MB chunks
                                f.write(chunk)
                                downloaded += len(chunk)
                        download_success = True
                        break

        if not download_success:
            return False

        # Stream JSON records from ZIP into a single NDJSON file for DuckDB
        ndjson_path = tmpdir / "records.ndjson"

        with timed("extract+flatten"):
            total_records = 0
            with zipfile.ZipFile(zip_path) as zf, Path(ndjson_path).open("w") as out:
                for name in zf.namelist():
                    if name.endswith(".json"):
                        with zf.open(name) as f:
                            data = json.load(f)
                            # Handle {count, items} wrapper
                            items = data.get("items", [data] if "id" in data else [])
                            for item in items:
                                out.write(json.dumps(item) + "\n")
                                total_records += 1

        if total_records == 0:
            return False

        # Create DuckDB connection with optimized settings
        con = duckdb.connect(
            config={
                "threads": "4",
                "memory_limit": "4GB",
            },
        )
        con.create_function("uuid5_djen", generate_uuid, [str], str)

        # Load NDJSON directly into DuckDB (very fast)
        with timed("load json"):
            con.execute(f"""
                CREATE TABLE comunicacoes_raw AS
                SELECT * FROM read_json_auto('{ndjson_path}',
                    format='newline_delimited',
                    maximum_object_size=104857600,
                    ignore_errors=true
                )
            """)
            con.execute("SELECT COUNT(*) FROM comunicacoes_raw").fetchone()[0]

        # Normalize using SQL
        with timed("normalize"):
            # 1. Comunicacoes (main table)
            con.execute(f"""
                CREATE TABLE comunicacoes AS
                SELECT
                    CAST(id AS VARCHAR) as id,
                    COALESCE(numero_processo, '') as numero_processo,
                    COALESCE(siglaTribunal, '{tribunal}') as tribunal,
                    COALESCE(data_disponibilizacao, '{date}') as data_disponibilizacao,
                    COALESCE(nomeOrgao, '') as orgao,
                    COALESCE(tipoComunicacao, '') as tipo,
                    CASE WHEN texto IS NOT NULL AND texto != ''
                         THEN uuid5_djen(texto)
                         ELSE NULL
                    END as texto_id,
                    COALESCE(nomeClasse, '') as classe,
                    COALESCE(numeroComunicacao, '') as numero_comunicacao,
                    COALESCE(status, '') as status
                FROM comunicacoes_raw
            """)

            # 2. Textos (deduplicated - compute UUID only on unique texts)
            con.execute("""
                CREATE TABLE textos AS
                WITH unique_texts AS (
                    SELECT DISTINCT texto
                    FROM comunicacoes_raw
                    WHERE texto IS NOT NULL AND texto != ''
                )
                SELECT
                    uuid5_djen(texto) as texto_id,
                    texto,
                    LENGTH(texto) as tamanho
                FROM unique_texts
            """)

            # 3. Partes from destinatarios (optimized with GROUP BY)
            con.execute("""
                CREATE TABLE partes AS
                SELECT
                    uuid5_djen(d.nome) as parte_id,
                    d.nome as nome,
                    '' as documento
                FROM comunicacoes_raw c,
                     LATERAL UNNEST(c.destinatarios) as t(d)
                WHERE c.destinatarios IS NOT NULL
                  AND d.nome IS NOT NULL AND d.nome != ''
                GROUP BY d.nome
            """)

            # 4. Comunicacao-Partes (association)
            con.execute("""
                CREATE TABLE comunicacao_partes AS
                SELECT
                    CAST(c.id AS VARCHAR) as comunicacao_id,
                    uuid5_djen(d.nome) as parte_id,
                    COALESCE(d.polo, '') as papel
                FROM comunicacoes_raw c,
                     LATERAL UNNEST(c.destinatarios) as t(d)
                WHERE c.destinatarios IS NOT NULL
                  AND d.nome IS NOT NULL AND d.nome != ''
            """)

            # 5. Advogados from destinatarioadvogados.advogado (optimized)
            con.execute("""
                CREATE TABLE advogados AS
                WITH advogado_keys AS (
                    SELECT
                        da.advogado.nome as nome,
                        COALESCE(da.advogado.numero_oab, '') as oab,
                        COALESCE(da.advogado.uf_oab, '') as uf
                    FROM comunicacoes_raw c,
                         LATERAL UNNEST(c.destinatarioadvogados) as t(da)
                    WHERE c.destinatarioadvogados IS NOT NULL
                      AND (da.advogado.nome IS NOT NULL OR da.advogado.numero_oab IS NOT NULL)
                    GROUP BY da.advogado.nome, da.advogado.numero_oab, da.advogado.uf_oab
                )
                SELECT
                    uuid5_djen(CONCAT(oab, '|', uf, '|', COALESCE(nome, ''))) as advogado_id,
                    nome,
                    oab,
                    uf
                FROM advogado_keys
            """)

            # 6. Comunicacao-Advogados (association)
            con.execute("""
                CREATE TABLE comunicacao_advogados AS
                SELECT
                    CAST(c.id AS VARCHAR) as comunicacao_id,
                    uuid5_djen(CONCAT(
                        COALESCE(da.advogado.numero_oab, ''), '|',
                        COALESCE(da.advogado.uf_oab, ''), '|',
                        COALESCE(da.advogado.nome, '')
                    )) as advogado_id
                FROM comunicacoes_raw c,
                     LATERAL UNNEST(c.destinatarioadvogados) as t(da)
                WHERE c.destinatarioadvogados IS NOT NULL
                  AND (da.advogado.nome IS NOT NULL OR da.advogado.numero_oab IS NOT NULL)
            """)

        # Write Parquet files
        out_dir = tmpdir / "parquet"
        out_dir.mkdir()

        tables = [
            "comunicacoes",
            "textos",
            "partes",
            "advogados",
            "comunicacao_partes",
            "comunicacao_advogados",
        ]

        with timed("write parquet"):
            for table in tables:
                filename = f"djen-{date}-{tribunal}-{table}.parquet"
                path = out_dir / filename
                # Write with optimized compression (level 3 balances speed/size)
                con.execute(f"""
                    COPY {table} TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD, COMPRESSION_LEVEL 3)
                """)
                if path.exists() and path.stat().st_size > 0:
                    con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    path.stat().st_size / 1024

        # Upload to Internet Archive (existing item)

        files = list(out_dir.glob("*.parquet"))
        if not files:
            return False

        with timed("upload"):
            try:
                item = ia.get_item(item_id)
                item.upload(
                    [str(f) for f in files],
                    queue_derive=False,
                    verbose=False,
                    retries=3,
                )
            except Exception:
                return False

        return True


def process_item_safe(entry: str) -> tuple[str, bool, str]:
    """Wrapper for process_item that catches exceptions."""
    try:
        result = process_item(entry)
    except Exception:
        return (entry, False, traceback.format_exc())
    else:
        return (entry, result, "")


def main() -> None:
    if len(sys.argv) < MAGIC_VAL_2:
        sys.exit(1)

    batch_file = Path(sys.argv[1])
    if not batch_file.exists():
        sys.exit(1)

    # Read entries (DATE|TRIBUNAL format)
    entries = [line.strip() for line in batch_file.read_text().splitlines() if line.strip()]

    success = 0
    failed = 0
    total_start = time.time()

    if len(entries) == 1:
        # Single entry - no need for parallelism
        entry, result, error = process_item_safe(entries[0])
        if result:
            success += 1
        else:
            failed += 1
            if error:
                pass
    else:
        # Multiple entries - process in parallel
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(process_item_safe, entry): entry for entry in entries}

            for future in as_completed(futures):
                _entry, result, error = future.result()
                if result:
                    success += 1
                else:
                    failed += 1
                    if error:
                        pass

    total_elapsed = time.time() - total_start
    total_elapsed / len(entries) if entries else 0

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
