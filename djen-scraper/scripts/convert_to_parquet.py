#!/usr/bin/env python3
"""
Convert DJEN ZIP files from Internet Archive to Parquet tables using DuckDB.

Optimized version: reads JSON directly into DuckDB and normalizes with SQL.

Usage:
    python convert_to_parquet.py batch.txt
"""

import subprocess
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path

import duckdb

# UUIDv5 namespace for DJEN
NAMESPACE_DJEN = uuid.uuid5(uuid.NAMESPACE_DNS, 'djen.jus.br')


def generate_uuid(content: str) -> str:
    """Generate deterministic UUIDv5 from content."""
    return str(uuid.uuid5(NAMESPACE_DJEN, content))


def process_item(item_id: str) -> bool:
    """Process a single Internet Archive item."""
    # Parse item_id: djen-raw-2026-01-21-TJSP
    parts = item_id.replace('djen-raw-', '').rsplit('-', 1)
    date = parts[0]
    tribunal = parts[1]

    print(f"\n{'='*60}")
    print(f"Processing: {item_id}")
    print(f"  Date: {date}, Tribunal: {tribunal}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Download from IA
        print("  Downloading from Internet Archive...")
        result = subprocess.run(
            ['ia', 'download', item_id, '--destdir', str(tmpdir)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"  ERROR: Download failed: {result.stderr}")
            return False

        # Find ZIP file
        zip_path = tmpdir / item_id / 'caderno.zip'
        if not zip_path.exists():
            zips = list((tmpdir / item_id).glob('*.zip'))
            if zips:
                zip_path = zips[0]
            else:
                print("  ERROR: ZIP not found")
                return False

        # Extract JSON files from ZIP to temp dir for DuckDB to read
        json_dir = tmpdir / 'json'
        json_dir.mkdir()

        print("  Extracting JSON from ZIP...")
        with zipfile.ZipFile(zip_path) as zf:
            json_files = [n for n in zf.namelist() if n.endswith('.json')]
            for name in json_files:
                zf.extract(name, json_dir)

        if not json_files:
            print("  WARNING: No JSON files found")
            return False

        # Create DuckDB connection and register UUID function
        con = duckdb.connect()
        con.create_function('uuid5_djen', generate_uuid, [str], str)

        # Read all JSON files - they have {count, items} wrapper structure
        print("  Loading JSON into DuckDB...")
        json_glob = str(json_dir / '*.json')

        # Unnest the items array from the wrapper
        con.execute(f"""
            CREATE TABLE raw AS
            SELECT UNNEST(items) as item
            FROM read_json_auto('{json_glob}',
                union_by_name=true,
                maximum_object_size=104857600,
                ignore_errors=true
            )
        """)

        # Flatten the nested structure
        con.execute("""
            CREATE TABLE comunicacoes_raw AS
            SELECT item.* FROM raw
        """)

        total_records = con.execute("SELECT COUNT(*) FROM comunicacoes_raw").fetchone()[0]
        print(f"  Loaded {total_records} records")

        if total_records == 0:
            print("  WARNING: No records loaded")
            return False

        # Normalize using SQL
        print("  Normalizing with SQL...")

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

        # 2. Textos (deduplicated by content)
        con.execute("""
            CREATE TABLE textos AS
            SELECT DISTINCT
                uuid5_djen(texto) as texto_id,
                texto,
                LENGTH(texto) as tamanho
            FROM comunicacoes_raw
            WHERE texto IS NOT NULL AND texto != ''
        """)

        # 3. Partes from destinatarios (deduplicated by nome)
        con.execute("""
            CREATE TABLE partes AS
            SELECT DISTINCT
                uuid5_djen(nome) as parte_id,
                nome,
                '' as documento
            FROM (
                SELECT UNNEST(destinatarios).nome as nome
                FROM comunicacoes_raw
                WHERE destinatarios IS NOT NULL
            )
            WHERE nome IS NOT NULL AND nome != ''
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

        # 5. Advogados from destinatarioadvogados.advogado (deduplicated)
        con.execute("""
            CREATE TABLE advogados AS
            SELECT DISTINCT
                uuid5_djen(CONCAT(
                    COALESCE(numero_oab, ''), '|',
                    COALESCE(uf_oab, ''), '|',
                    COALESCE(nome, '')
                )) as advogado_id,
                nome,
                COALESCE(numero_oab, '') as oab,
                COALESCE(uf_oab, '') as uf
            FROM (
                SELECT
                    da.advogado.nome as nome,
                    da.advogado.numero_oab as numero_oab,
                    da.advogado.uf_oab as uf_oab
                FROM comunicacoes_raw c,
                     LATERAL UNNEST(c.destinatarioadvogados) as t(da)
                WHERE c.destinatarioadvogados IS NOT NULL
            )
            WHERE nome IS NOT NULL OR numero_oab IS NOT NULL
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
        out_dir = tmpdir / 'parquet'
        out_dir.mkdir()

        tables = ['comunicacoes', 'textos', 'partes', 'advogados',
                  'comunicacao_partes', 'comunicacao_advogados']

        for table in tables:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if count > 0:
                path = out_dir / f"{table}.parquet"
                con.execute(f"""
                    COPY {table} TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD)
                """)
                print(f"    {table}: {count} rows")

        # Upload to Internet Archive
        parquet_id = f"djen-parquet-{date}-{tribunal}"
        print(f"  Uploading to IA: {parquet_id}")

        files = list(out_dir.glob('*.parquet'))
        if not files:
            print("  WARNING: No parquet files to upload")
            return False

        cmd = [
            'ia', 'upload', parquet_id,
            *[str(f) for f in files],
            '--metadata=collection:opensource',
            '--metadata=mediatype:data',
            f'--metadata=title:DJEN Parquet {tribunal} {date}',
            f'--metadata=description:Normalized Parquet tables from DJEN {tribunal} {date}',
            f'--metadata=subject:brazilian-law;djen;legal;judiciary;parquet;{tribunal}',
            '--metadata=creator:CausaGanha',
            f'--metadata=date:{date}',
            f'--metadata=tribunal:{tribunal}',
            f'--metadata=source_item:{item_id}',
            f'--metadata=total_comunicacoes:{total_records}',
            '--retries=3',
            '--no-derive'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ERROR: Upload failed: {result.stderr}")
            return False

        print("  Done!")
        return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_to_parquet.py <batch_file>")
        print("  batch_file: file with one item ID per line")
        sys.exit(1)

    batch_file = Path(sys.argv[1])
    if not batch_file.exists():
        print(f"ERROR: File not found: {batch_file}")
        sys.exit(1)

    # Read items
    items = [line.strip() for line in batch_file.read_text().splitlines() if line.strip()]
    print(f"Processing {len(items)} items using DuckDB")

    success = 0
    failed = 0

    for item_id in items:
        try:
            if process_item(item_id):
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print(f"SUMMARY: {success} success, {failed} failed")

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
