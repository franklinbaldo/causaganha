from __future__ import annotations

import json
import zipfile
from pathlib import Path

import ibis
import pyarrow.parquet as pq

from causaganha.consolidate.exporter import export_table_sync
from causaganha.consolidate.schema_registry import CURRENT_VERSION, get_current_schema
from causaganha.consolidate.transforms import TABLES, init_tables, load_and_transform
from causaganha.consolidate.zip_processor import stream_zip_to_ndjson


def _minimal_record() -> dict[str, object]:
    return {
        "id": "pub-1",
        "texto": "JULGO PROCEDENTE o pedido.",
        "numeroProcesso": "0001234-56.2026.8.26.0100",
        "dataDisponibilizacao": "2026-04-01",
        "tipoComunicacao": "Intimação",
        "nomeOrgao": "1ª Vara Cível",
        "meio": "Eletrônico",
        "link": "https://example.test/pub-1",
        "tipoDocumento": "Sentença",
        "nomeClasse": "Procedimento Comum",
        "codigoClasse": "7",
        "numeroComunicacao": "001",
        "hash": "abc123",
        "destinatarios": [{"nome": "JOÃO DA SILVA", "polo": "Ativo"}],
        "destinatarioadvogados": [
            {"advogado": {"nome": "DRA MARIA OLIVEIRA", "numeroOAB": "12345", "ufOAB": "SP"}}
        ],
    }


def test_minimal_zip_to_consolidated_parquet_schema_contract(tmp_path: Path) -> None:
    zip_path = tmp_path / "djen-2026-04-01-TJSP.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("comunicacoes.json", json.dumps({"items": [_minimal_record()]}))

    ndjson_dir = tmp_path / "ndjson"
    ndjson_dir.mkdir()
    ndjson_path = ndjson_dir / "TJSP__djen-2026-04-01-TJSP.ndjson"
    assert stream_zip_to_ndjson(zip_path, ndjson_path, "TJSP") == 1

    con = ibis.duckdb.connect()
    init_tables(con)
    counts = load_and_transform(con, ndjson_dir, item_id="djen-tjsp-2026")
    assert counts == dict.fromkeys(TABLES, 1)

    parquet_dir = tmp_path / "parquet"
    parquet_dir.mkdir()
    exported = export_table_sync("comunicacoes", con, parquet_dir, item_id="djen-tjsp-2026")
    assert exported is not None

    parquet_path, _size_mb, row_count = exported
    assert row_count == 1
    arrow_schema = pq.read_schema(parquet_path)
    expected = get_current_schema().tables["comunicacoes"]
    assert arrow_schema.names == list(expected.names)
    assert arrow_schema.metadata is not None
    assert arrow_schema.metadata[b"causaganha.schema_version"].decode() == CURRENT_VERSION
    assert arrow_schema.metadata[b"causaganha.item_id"].decode() == "djen-tjsp-2026"
