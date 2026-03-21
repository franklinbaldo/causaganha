import pytest
from scripts.generate_catalog import parse_filename

def test_parse_filename_zip():
    item_id = "djen-tjsp-2026"
    filename = "djen-2026-01-15-TJSP.zip"
    res = parse_filename(filename, item_id)
    assert res is not None
    assert res["date"] == "2026-01-15"
    assert res["tribunal"] == "TJSP"
    assert res["file_type"] == "zip"

def test_parse_filename_absent():
    item_id = "djen-tre-ac-2026"
    filename = "djen-2026-01-15-TRE-AC.absent"
    res = parse_filename(filename, item_id)
    assert res is not None
    assert res["date"] == "2026-01-15"
    assert res["tribunal"] == "TRE-AC"
    assert res["file_type"] == "absent"

def test_parse_filename_parquet():
    item_id = "djen-tjsp-2026"
    filename = "TJSP-2026-01-15-comunicacoes.parquet"
    res = parse_filename(filename, item_id)
    assert res is not None
    assert res["date"] == "2026-01-15"
    assert res["tribunal"] == "TJSP"
    assert res["file_type"] == "parquet"
    assert res["table_name"] == "comunicacoes"

def test_parse_filename_parquet_legacy():
    item_id = "djen-2026-01-15"
    filename = "djen-2026-01-15-TJSP-comunicacoes.parquet"
    res = parse_filename(filename, item_id)
    assert res is not None
    assert res["date"] == "2026-01-15"
    assert res["tribunal"] == "TJSP"
    assert res["file_type"] == "parquet"
    assert res["table_name"] == "comunicacoes"
