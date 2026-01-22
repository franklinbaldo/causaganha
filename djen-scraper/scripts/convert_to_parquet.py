#!/usr/bin/env python3
"""
Convert DJEN ZIP files from Internet Archive to Parquet tables.

Usage:
    python convert_to_parquet.py batch.txt

Where batch.txt contains one item ID per line (e.g., djen-raw-2026-01-21-TJSP)
"""

import json
import subprocess
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

# UUIDv5 namespace for DJEN
NAMESPACE_DJEN = uuid.uuid5(uuid.NAMESPACE_DNS, 'djen.jus.br')


def generate_uuid(content: str) -> str:
    """Generate deterministic UUIDv5 from content."""
    return str(uuid.uuid5(NAMESPACE_DJEN, content))


def extract_zip(zip_path: Path) -> list:
    """Extract JSON records from ZIP file."""
    records = []
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for name in zf.namelist():
            if name.endswith('.json'):
                with zf.open(name) as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        records.extend(data)
                    else:
                        records.append(data)
    return records


def normalize(records: list, date: str, tribunal: str) -> dict:
    """Normalize records into relational tables."""
    textos_seen, partes_seen, advogados_seen = {}, {}, {}
    comunicacoes, textos, partes, advogados = [], [], [], []
    comunicacao_partes, comunicacao_advogados = [], []

    for r in records:
        cid = r.get('id', generate_uuid(json.dumps(r)))

        # Texto - deduplicate by content hash
        texto = r.get('texto', '')
        texto_id = generate_uuid(texto) if texto else None
        if texto and texto_id not in textos_seen:
            textos_seen[texto_id] = True
            textos.append({
                'texto_id': texto_id,
                'texto': texto,
                'tamanho': len(texto)
            })

        # Main comunicacao record
        comunicacoes.append({
            'id': cid,
            'numero_processo': r.get('numeroProcesso', '') or r.get('numero_processo', ''),
            'tribunal': tribunal,
            'data_disponibilizacao': date,
            'orgao': r.get('orgao', {}).get('nome', '') if isinstance(r.get('orgao'), dict) else str(r.get('orgao', '')),
            'tipo': r.get('tipoComunicacao', '') or r.get('tipo', ''),
            'texto_id': texto_id,
            'sigiloso': r.get('sigiloso', False),
        })

        # Partes - deduplicate by nome|documento
        for p in r.get('partes', []):
            if isinstance(p, dict):
                nome = p.get('nome', '')
                doc = p.get('documento', '') or p.get('cpfCnpj', '')
                papel = p.get('tipo', '') or p.get('papel', '')
            else:
                nome, doc, papel = str(p), '', ''

            if nome:
                pid = generate_uuid(f"{nome}|{doc}")
                if pid not in partes_seen:
                    partes_seen[pid] = True
                    partes.append({
                        'parte_id': pid,
                        'nome': nome,
                        'documento': doc
                    })
                comunicacao_partes.append({
                    'comunicacao_id': cid,
                    'parte_id': pid,
                    'papel': papel
                })

        # Advogados - deduplicate by oab|uf|nome
        for a in r.get('advogados', []):
            if isinstance(a, dict):
                nome = a.get('nome', '')
                oab = a.get('oab', '') or a.get('numeroOAB', '')
                uf = a.get('uf', '') or a.get('ufOAB', '')
            else:
                nome, oab, uf = str(a), '', ''

            if nome or oab:
                aid = generate_uuid(f"{oab}|{uf}|{nome}")
                if aid not in advogados_seen:
                    advogados_seen[aid] = True
                    advogados.append({
                        'advogado_id': aid,
                        'nome': nome,
                        'oab': oab,
                        'uf': uf
                    })
                comunicacao_advogados.append({
                    'comunicacao_id': cid,
                    'advogado_id': aid
                })

    return {
        'comunicacoes': comunicacoes,
        'textos': textos,
        'partes': partes,
        'advogados': advogados,
        'comunicacao_partes': comunicacao_partes,
        'comunicacao_advogados': comunicacao_advogados
    }


def write_parquet(data: list, path: Path):
    """Write data to Parquet with zstd compression."""
    if data:
        table = pa.Table.from_pylist(data)
        pq.write_table(table, path, compression='zstd', row_group_size=10000)


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
        print(f"  Downloading from Internet Archive...")
        result = subprocess.run(
            ['ia', 'download', item_id, '-d', str(tmpdir)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"  ERROR: Download failed: {result.stderr}")
            return False

        # Find ZIP file
        zip_path = tmpdir / item_id / 'caderno.zip'
        if not zip_path.exists():
            # Try finding any zip
            zips = list((tmpdir / item_id).glob('*.zip'))
            if zips:
                zip_path = zips[0]
            else:
                print(f"  ERROR: ZIP not found")
                return False

        # Extract records
        print(f"  Extracting...")
        records = extract_zip(zip_path)
        print(f"  Found {len(records)} records")

        if not records:
            print(f"  WARNING: No records found")
            return False

        # Normalize to relational tables
        print(f"  Normalizing...")
        tables = normalize(records, date, tribunal)

        # Write Parquet files
        out_dir = tmpdir / 'parquet'
        out_dir.mkdir()

        for name, data in tables.items():
            if data:
                path = out_dir / f"{name}.parquet"
                write_parquet(data, path)
                print(f"    {name}: {len(data)} rows")

        # Upload to Internet Archive
        parquet_id = f"djen-parquet-{date}-{tribunal}"
        print(f"  Uploading to IA: {parquet_id}")

        files = list(out_dir.glob('*.parquet'))
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
            '--retries=3',
            '--no-derive'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ERROR: Upload failed: {result.stderr}")
            return False

        print(f"  ✅ Done!")
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
    print(f"Processing {len(items)} items")

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
            failed += 1

    print(f"\n{'='*60}")
    print(f"SUMMARY: {success} success, {failed} failed")

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
