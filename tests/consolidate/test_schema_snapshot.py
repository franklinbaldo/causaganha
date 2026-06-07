"""Tests for schema validation, Parquet footer stamping, and roundtrip equivalence."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from causaganha.consolidate.schema_registry import CURRENT_VERSION, get_current_schema
from causaganha.consolidate.validation import (
    validate_ndjson_record,
    validate_parquet_schema,
    validate_roundtrip_equivalence,
)


SCHEMA_VERSION = CURRENT_VERSION.split(".")[0]
TABLE_SCHEMAS = get_current_schema().tables
TABLES = list(TABLE_SCHEMAS.keys())


def test_schema_version_is_3():
    assert SCHEMA_VERSION == "3"


def test_validate_ndjson_record():
    # Valid
    assert (
        validate_ndjson_record(
            {
                "id": "12345",
                "data_disponibilizacao": "2026-04-01",
            }
        )
        is True
    )

    # Missing ID
    assert (
        validate_ndjson_record(
            {
                "data_disponibilizacao": "2026-04-01",
            }
        )
        is False
    )

    # Empty ID
    assert (
        validate_ndjson_record(
            {
                "id": "  ",
                "data_disponibilizacao": "2026-04-01",
            }
        )
        is False
    )

    # Missing Date
    assert (
        validate_ndjson_record(
            {
                "id": "12345",
            }
        )
        is False
    )

    # Invalid Date length
    assert (
        validate_ndjson_record(
            {
                "id": "12345",
                "data_disponibilizacao": "202",
            }
        )
        is False
    )


def test_parquet_validation(tmp_path):
    # Create dummy parquet file matching 'comunicacoes' columns
    fields = []
    data = []
    for name, expected_type in TABLE_SCHEMAS["comunicacoes"].items():
        expected_type_str = str(expected_type).lower()
        if "string" in expected_type_str:
            arrow_type = pa.string()
            val = ["dummy"]
        elif "int32" in expected_type_str:
            arrow_type = pa.int32()
            val = [1]
        elif "int64" in expected_type_str:
            arrow_type = pa.int64()
            val = [1]
        elif "date" in expected_type_str:
            arrow_type = pa.date32()
            val = [date(2026, 4, 1)]
        elif "timestamp" in expected_type_str:
            arrow_type = pa.timestamp("us")
            val = [datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)]
        else:
            arrow_type = pa.string()
            val = ["dummy"]
        fields.append(pa.field(name, arrow_type))
        data.append(val)

    schema = pa.schema(fields)
    table = pa.Table.from_arrays(data, schema=schema)
    parquet_path = tmp_path / "comunicacoes.parquet"
    pq.write_table(table, parquet_path)

    # Validate -> should pass
    validate_parquet_schema(parquet_path, "comunicacoes")

    # Test with wrong table name validation -> should fail due to column mismatch
    with pytest.raises(ValueError, match="Schema column mismatch"):
        validate_parquet_schema(parquet_path, "advogados")


def test_validate_roundtrip_equivalence(tmp_path):
    ndjson_dir = tmp_path / "ndjson"
    ndjson_dir.mkdir()
    parquet_dir = tmp_path / "parquet"
    parquet_dir.mkdir()

    # Create dummy NDJSON
    ndjson_file = ndjson_dir / "TJSP__sample.ndjson"
    rec1 = {
        "id": "rec-1",
        "data_disponibilizacao": "2026-04-01",
        "texto": "Decisão judicial de teste 1",
    }
    rec2 = {
        "id": "rec-2",
        "data_disponibilizacao": "2026-04-01",
        "texto": "Decisão judicial de teste 2",
    }
    with ndjson_file.open("w", encoding="utf-8") as f:
        f.write(json.dumps(rec1) + "\n")
        f.write(json.dumps(rec2) + "\n")

    # Create matching Parquet tables
    # 1. comunicacoes.parquet
    com_fields = [
        pa.field("id", pa.string()),
        pa.field("original_id", pa.string()),
        pa.field("texto_id", pa.string()),
        pa.field("tribunal", pa.string()),
        pa.field("numero_processo", pa.string()),
        pa.field("numero_processo_mascara", pa.string()),
        pa.field("data_disponibilizacao", pa.date32()),
        pa.field("tipo_comunicacao", pa.string()),
        pa.field("nome_orgao", pa.string()),
        pa.field("meio", pa.string()),
        pa.field("link", pa.string()),
        pa.field("tipo_documento", pa.string()),
        pa.field("nome_classe", pa.string()),
        pa.field("codigo_classe", pa.string()),
        pa.field("numero_comunicacao", pa.string()),
        pa.field("hash", pa.string()),
        pa.field("processed_at", pa.timestamp("us")),
        pa.field("p_ano", pa.int32()),
        pa.field("p_mes", pa.int32()),
        pa.field("p_item_ia", pa.string()),
    ]
    com_data = [
        ["uuid-1", "uuid-2"],  # id
        ["rec-1", "rec-2"],  # original_id
        ["txt-1", "txt-2"],  # texto_id
        ["TJSP", "TJSP"],  # tribunal
        ["", ""],  # numero_processo
        ["", ""],  # numero_processo_mascara
        [date(2026, 4, 1), date(2026, 4, 1)],  # data_disponibilizacao
        ["", ""],  # tipo_comunicacao
        ["", ""],  # nome_orgao
        ["", ""],  # meio
        ["", ""],  # link
        ["", ""],  # tipo_documento
        ["", ""],  # nome_classe
        ["", ""],  # codigo_classe
        ["", ""],  # numero_comunicacao
        ["", ""],  # hash
        [
            datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC),
            datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC),
        ],  # processed_at
        [2026, 2026],  # p_ano
        [4, 4],  # p_mes
        ["djen-2026-04-01", "djen-2026-04-01"],  # p_item_ia
    ]
    com_table = pa.Table.from_arrays(com_data, schema=pa.schema(com_fields))
    pq.write_table(com_table, parquet_dir / "comunicacoes.parquet")

    # 2. textos.parquet
    txt_fields = [
        pa.field("id", pa.string()),
        pa.field("texto", pa.string()),
    ]
    txt_data = [
        ["txt-1", "txt-2"],  # id
        ["Decisão judicial de teste 1", "Decisão judicial de teste 2"],  # texto
    ]
    txt_table = pa.Table.from_arrays(txt_data, schema=pa.schema(txt_fields))
    pq.write_table(txt_table, parquet_dir / "textos.parquet")

    # Run roundtrip equivalence check -> should pass
    validate_roundtrip_equivalence(ndjson_dir, parquet_dir)

    # Test roundtrip mismatch: modify NDJSON to have different text
    with ndjson_file.open("w", encoding="utf-8") as f:
        f.write(json.dumps(rec1) + "\n")
        f.write(json.dumps({**rec2, "texto": "Decisão judicial alterada"}) + "\n")

    with pytest.raises(ValueError, match="Roundtrip equivalence failed: Text mismatch"):
        validate_roundtrip_equivalence(ndjson_dir, parquet_dir)


def test_ts_schema_snapshot_parity():
    ts_path = Path("web/src/lib/consolidated-schemas.ts")
    assert ts_path.exists()
    content = ts_path.read_text(encoding="utf-8")

    assert 'export const CONSOLIDATED_SCHEMA_VERSION = "3";' in content

    # Assert that all consolidated tables have schemas defined in TS
    for table in TABLES:
        expected_schema_name = f"{table}Schema"
        if "_" in table:
            parts = table.split("_")
            camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
            expected_schema_name_alt = f"{camel}Schema"
        else:
            expected_schema_name_alt = expected_schema_name

        assert (expected_schema_name in content) or (expected_schema_name_alt in content), (
            f"Expected schema definition for '{table}' in TS file"
        )
