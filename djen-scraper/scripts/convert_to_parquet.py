#!/usr/bin/env python3
"""
Convert DJEN ZIP files to Parquet tables.

This script:
1. Downloads raw ZIPs from Internet Archive
2. Extracts and normalizes JSON data
3. Creates relational Parquet tables with:
   - Deduplication via UUIDv5
   - Internal partitioning for efficient queries
4. Uploads Parquet files back to Internet Archive
"""

import json
import os
import subprocess
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

# UUIDv5 namespace for DJEN
NAMESPACE_DJEN = uuid.uuid5(uuid.NAMESPACE_DNS, 'djen.jus.br')


def generate_uuid(content: str) -> str:
    """Generate deterministic UUIDv5 from content."""
    return str(uuid.uuid5(NAMESPACE_DJEN, content))


def extract_zip(zip_path: Path) -> list[dict]:
    """Extract JSON records from ZIP file."""
    records = []
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for name in zf.namelist():
            if name.endswith('.json'):
                with zf.open(name) as f:
                    data = json.load(f)
                    # Handle both single record and array
                    if isinstance(data, list):
                        records.extend(data)
                    else:
                        records.append(data)
    return records


def normalize_records(records: list[dict], date: str, tribunal: str) -> dict[str, list]:
    """
    Normalize records into relational tables.

    Returns dict with keys:
    - comunicacoes: main fact table
    - textos: deduplicated text content
    - partes: unique parties
    - advogados: unique lawyers
    - comunicacao_partes: association table
    - comunicacao_advogados: association table
    """

    # Deduplication sets
    textos_seen = {}
    partes_seen = {}
    advogados_seen = {}

    # Output tables
    comunicacoes = []
    textos = []
    partes = []
    advogados = []
    comunicacao_partes = []
    comunicacao_advogados = []

    for record in records:
        comunicacao_id = record.get('id', generate_uuid(json.dumps(record)))

        # Extract texto and deduplicate
        texto_content = record.get('texto', '')
        if texto_content:
            texto_id = generate_uuid(texto_content)
            if texto_id not in textos_seen:
                textos_seen[texto_id] = True
                textos.append({
                    'texto_id': texto_id,
                    'texto': texto_content,
                    'tamanho_bytes': len(texto_content.encode('utf-8'))
                })
        else:
            texto_id = None

        # Extract numero_processo for partitioning
        numero_processo = record.get('numeroProcesso', '') or record.get('numero_processo', '')

        # Main comunicacao record
        comunicacoes.append({
            'id': comunicacao_id,
            'numero_processo': numero_processo,
            'tribunal': tribunal,
            'data_disponibilizacao': date,
            'orgao': record.get('orgao', {}).get('nome', '') if isinstance(record.get('orgao'), dict) else str(record.get('orgao', '')),
            'tipo': record.get('tipoComunicacao', '') or record.get('tipo', ''),
            'meio': record.get('meio', 'D'),
            'caderno': record.get('caderno', ''),
            'texto_id': texto_id,
            'sigiloso': record.get('sigiloso', False),
            'hash_original': record.get('hash', ''),
        })

        # Process partes
        for parte_data in record.get('partes', []):
            if isinstance(parte_data, dict):
                nome = parte_data.get('nome', '')
                documento = parte_data.get('documento', '') or parte_data.get('cpfCnpj', '')
                papel = parte_data.get('tipo', '') or parte_data.get('papel', '')
            else:
                nome = str(parte_data)
                documento = ''
                papel = ''

            if nome:
                parte_id = generate_uuid(f"{nome}|{documento}")
                if parte_id not in partes_seen:
                    partes_seen[parte_id] = True
                    partes.append({
                        'parte_id': parte_id,
                        'nome': nome,
                        'documento': documento,
                    })

                comunicacao_partes.append({
                    'comunicacao_id': comunicacao_id,
                    'parte_id': parte_id,
                    'papel': papel,
                })

        # Process advogados
        for adv_data in record.get('advogados', []):
            if isinstance(adv_data, dict):
                nome = adv_data.get('nome', '')
                oab = adv_data.get('oab', '') or adv_data.get('numeroOAB', '')
                uf = adv_data.get('uf', '') or adv_data.get('ufOAB', '')
            else:
                nome = str(adv_data)
                oab = ''
                uf = ''

            if nome or oab:
                advogado_id = generate_uuid(f"{oab}|{uf}|{nome}")
                if advogado_id not in advogados_seen:
                    advogados_seen[advogado_id] = True
                    advogados.append({
                        'advogado_id': advogado_id,
                        'nome': nome,
                        'oab': oab,
                        'uf': uf,
                    })

                # Link to parte if available
                representa_parte_id = None
                if isinstance(adv_data, dict) and adv_data.get('parte'):
                    parte_nome = adv_data['parte'].get('nome', '') if isinstance(adv_data['parte'], dict) else str(adv_data['parte'])
                    representa_parte_id = generate_uuid(f"{parte_nome}|")

                comunicacao_advogados.append({
                    'comunicacao_id': comunicacao_id,
                    'advogado_id': advogado_id,
                    'representa_parte_id': representa_parte_id,
                })

    return {
        'comunicacoes': comunicacoes,
        'textos': textos,
        'partes': partes,
        'advogados': advogados,
        'comunicacao_partes': comunicacao_partes,
        'comunicacao_advogados': comunicacao_advogados,
    }


def write_parquet_table(data: list[dict], path: Path, partition_cols: list[str] | None = None):
    """Write data to Parquet with optional partitioning."""
    if not data:
        return

    table = pa.Table.from_pylist(data)

    # Write with row group size for efficient filtering
    pq.write_table(
        table,
        path,
        row_group_size=10000,  # ~10k rows per group for efficient filtering
        compression='zstd',
    )


def process_item(item_id: str, work_dir: Path):
    """Process a single Internet Archive item."""
    # Parse item_id: djen-raw-2026-01-21-TJSP
    parts = item_id.replace('djen-raw-', '').rsplit('-', 1)
    date = parts[0]  # 2026-01-21
    tribunal = parts[1]  # TJSP

    print(f"Processing: {date} / {tribunal}")

    # Download from IA
    zip_path = work_dir / 'caderno.zip'
    print(f"  Downloading from IA...")
    subprocess.run(
        ['ia', 'download', item_id, 'caderno.zip', '-d', str(work_dir)],
        check=True,
        capture_output=True
    )

    # Find the downloaded file
    zip_file = work_dir / item_id / 'caderno.zip'
    if not zip_file.exists():
        print(f"  ERROR: ZIP not found at {zip_file}")
        return False

    # Extract and process
    print(f"  Extracting...")
    records = extract_zip(zip_file)
    print(f"  Found {len(records)} records")

    if not records:
        print(f"  WARNING: No records found")
        return False

    # Normalize to tables
    print(f"  Normalizing...")
    tables = normalize_records(records, date, tribunal)

    # Create output directory
    output_dir = work_dir / 'parquet'
    output_dir.mkdir(exist_ok=True)

    # Write Parquet files
    print(f"  Writing Parquet files...")
    for name, data in tables.items():
        if data:
            path = output_dir / f"{name}.parquet"
            write_parquet_table(data, path)
            print(f"    {name}: {len(data)} rows")

    # Upload to IA
    parquet_item_id = f"djen-parquet-{date}-{tribunal}"
    print(f"  Uploading to IA: {parquet_item_id}")

    # Upload all parquet files
    parquet_files = list(output_dir.glob('*.parquet'))

    cmd = [
        'ia', 'upload', parquet_item_id,
        *[str(f) for f in parquet_files],
        '--metadata=collection:opensource',
        '--metadata=mediatype:data',
        f'--metadata=title:DJEN Parquet {tribunal} {date}',
        f'--metadata=description:Normalized Parquet tables from DJEN {tribunal} {date}',
        f'--metadata=subject:brazilian-law;djen;legal;judiciary;parquet;{tribunal}',
        '--metadata=creator:CausaGanha',
        f'--metadata=date:{date}',
        f'--metadata=tribunal:{tribunal}',
        f'--metadata=source_item:{item_id}',
        '--retries=3',
        '--no-derive',
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: Upload failed: {result.stderr}")
        return False

    print(f"  Done!")
    return True


def main():
    # Load items to convert
    with open('to_convert.json') as f:
        items = json.load(f)

    if not items:
        print("No items to convert")
        return

    print(f"Converting {len(items)} items")

    success = 0
    failed = 0

    for item_id in items:
        with tempfile.TemporaryDirectory() as work_dir:
            try:
                if process_item(item_id, Path(work_dir)):
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"  ERROR: {e}")
                failed += 1

    print(f"\nCompleted: {success} success, {failed} failed")


if __name__ == '__main__':
    main()
