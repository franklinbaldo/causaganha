"""Test parallel Parquet export with local ZIPs."""

import json
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import ibis
import pytest
import structlog

from scripts.pipeline.consolidate import (
    TABLE_SCHEMAS,
    TABLES,
    _load_and_transform,
    extract_json_from_zip,
    init_tables,
)


logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Synthetic data tests (no external ZIPs required)
# ---------------------------------------------------------------------------

SAMPLE_RECORD = {
    "id": "12345",
    "texto": "JULGO PROCEDENTE o pedido do autor para condenar o réu.",
    "numeroProcesso": "0001234-56.2026.8.26.0100",
    "dataDisponibilizacao": "2026-04-01",
    "tipoComunicacao": "Intimação",
    "nomeOrgao": "1ª Vara Cível",
    "meio": "Eletrônico",
    "link": "https://example.com",
    "tipoDocumento": "Sentença",
    "nomeClasse": "Procedimento Comum",
    "codigoClasse": "7",
    "numeroComunicacao": "001",
    "hash": "abc123",
    # DJEN API provides destinatarios as flat array of parties
    "destinatarios": [
        {"nome": "JOÃO DA SILVA", "polo": "Ativo"},
        {"nome": "EMPRESA XYZ LTDA", "polo": "Passivo"},
    ],
    # DJEN API provides destinatarioadvogados as separate flat array
    "destinatarioadvogados": [
        {
            "advogado": {
                "nome": "DRA MARIA OLIVEIRA",
                "numeroOAB": "12345",
                "ufOAB": "SP",
            },
        },
        {
            "advogado": {
                "nome": "DR PEDRO SANTOS",
                "numeroOAB": "67890",
                "ufOAB": "SP",
            },
        },
    ],
}

SAMPLE_RECORD_IMPROCEDENTE = {
    **SAMPLE_RECORD,
    "id": "67890",
    "texto": "JULGO IMPROCEDENTE o pedido formulado pelo autor.",
    "hash": "def456",
}


def _create_synthetic_ndjson(ndjson_dir: Path) -> None:
    """Write synthetic NDJSON files mimicking ZIP extraction output."""
    records = [SAMPLE_RECORD, SAMPLE_RECORD_IMPROCEDENTE]
    ndjson_path = ndjson_dir / "TJSP__djen-2026-04-01-TJSP.ndjson"
    with ndjson_path.open("w") as f:
        for rec in records:
            f.write(json.dumps(rec, default=str) + "\n")


def test_all_tables_populated_from_synthetic_data():
    """Verify all 10 tables are produced from synthetic data, including classificacoes."""
    con = ibis.duckdb.connect()
    init_tables(con)

    with tempfile.TemporaryDirectory() as tmpdir:
        ndjson_dir = Path(tmpdir)
        _create_synthetic_ndjson(ndjson_dir)

        counts = _load_and_transform(con, ndjson_dir, item_id="djen-2026-04-01")

    # All tables should exist
    assert len(TABLES) == 10, f"Expected 10 tables, got {len(TABLES)}"

    # Core tables must have rows
    assert counts.get("comunicacoes", 0) > 0, "comunicacoes should have rows"
    assert counts.get("textos", 0) > 0, "textos should have rows"
    assert counts.get("advogados", 0) > 0, "advogados should have rows"
    assert counts.get("destinatarios", 0) > 0, "destinatarios should have rows"
    assert counts.get("processos", 0) > 0, "processos should have rows"

    # classificacoes should be populated (keyword match on "procedente" / "improcedente")
    assert counts.get("classificacoes", 0) > 0, (
        "classificacoes should have rows from keyword classification"
    )


def test_classificacoes_schema_correct():
    """Verify classificacoes table has the correct schema columns."""
    expected_cols = {
        "texto_id", "metodo", "outcome", "decision_type",
        "winner_advogado_id", "loser_advogado_id", "confidence", "classified_at",
    }
    schema = TABLE_SCHEMAS["classificacoes"]
    actual_cols = set(schema.names)
    assert actual_cols == expected_cols, f"Schema mismatch: {actual_cols} != {expected_cols}"


def test_classificacoes_outcomes():
    """Verify keyword classifier produces correct outcomes."""
    con = ibis.duckdb.connect()
    init_tables(con)

    with tempfile.TemporaryDirectory() as tmpdir:
        ndjson_dir = Path(tmpdir)
        _create_synthetic_ndjson(ndjson_dir)
        _load_and_transform(con, ndjson_dir, item_id="djen-2026-04-01")

    df = con.table("classificacoes").to_pandas()
    outcomes = set(df["outcome"].tolist())

    # Our sample data has "procedente" (WIN) and "improcedente" (LOSS)
    assert "WIN" in outcomes or "LOSS" in outcomes, (
        f"Expected WIN or LOSS in outcomes, got {outcomes}"
    )
    assert all(df["metodo"] == "keyword_v1"), "All classifications should use keyword_v1 method"
    assert all(df["confidence"] == 0.3), "Keyword classifier confidence should be 0.3"


def test_parquet_export_roundtrip():
    """Verify Parquet files can be created and read back with correct row counts."""
    con = ibis.duckdb.connect()
    init_tables(con)

    with tempfile.TemporaryDirectory() as tmpdir:
        ndjson_dir = Path(tmpdir) / "ndjson"
        ndjson_dir.mkdir()
        _create_synthetic_ndjson(ndjson_dir)
        counts = _load_and_transform(con, ndjson_dir, item_id="djen-2026-04-01")

        output_dir = Path(tmpdir) / "parquet"
        output_dir.mkdir()

        exported = 0
        for table_name in TABLES:
            t = con.table(table_name)
            count = t.count().execute()
            if count == 0:
                continue

            output_path = output_dir / f"{table_name}.parquet"
            con.raw_sql(
                f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD)"
            )
            assert output_path.exists(), f"{table_name}.parquet should exist"
            assert output_path.stat().st_size > 0, f"{table_name}.parquet should not be empty"

            # Read back and verify row count
            read_con = ibis.duckdb.connect()
            read_t = read_con.read_parquet(str(output_path))
            read_count = read_t.count().execute()
            assert read_count == count, (
                f"{table_name}: wrote {count} rows but read back {read_count}"
            )
            exported += 1

    assert exported >= 5, f"Should export at least 5 tables, got {exported}"


def _write_ndjson_from_zips(test_zip_dir: Path, ndjson_dir: Path) -> int:
    """Extract JSON from ZIPs and write NDJSON files for _load_and_transform."""
    total_records = 0
    for zip_file in sorted(test_zip_dir.glob("*.zip")):
        tribunal = zip_file.name.split("-")[-1].replace(".zip", "")

        records = extract_json_from_zip(zip_file)
        if not records:
            continue

        total_records += len(records)

        ndjson_path = ndjson_dir / f"{tribunal}__{zip_file.stem}.ndjson"
        with ndjson_path.open("w") as f:
            for rec in records:
                if isinstance(rec, dict):
                    f.write(json.dumps(rec, default=str) + "\n")

    return total_records


def test_parallel_export():
    """Test parallel Parquet export with local test ZIPs."""
    test_zip_dir = Path("test_zips")

    if not test_zip_dir.exists():
        pytest.skip("test_zips directory not found")

    # Set up test database
    con = ibis.duckdb.connect()
    init_tables(con)

    # Extract ZIPs to NDJSON and load via _load_and_transform
    with tempfile.TemporaryDirectory() as ndjson_tmpdir:
        ndjson_dir = Path(ndjson_tmpdir)
        total_records = _write_ndjson_from_zips(test_zip_dir, ndjson_dir)

        if total_records == 0:
            pytest.skip("no records extracted from test ZIPs")

        _load_and_transform(con, ndjson_dir, item_id="test-item")

    # Now test the parallel export

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "output"
        output_dir.mkdir()

        # Helper function (same as in consolidate.py)
        def _export_and_upload_table(table_name: str, con, output_dir: Path, *, _dry_run: bool):
            t = con.table(table_name)
            count = t.count().to_pandas()
            if count == 0:
                return False, 0, 0

            output_path = output_dir / f"{table_name}.parquet"
            start = time.time()
            con.raw_sql(
                f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD)",
            )
            elapsed = time.time() - start
            return True, 1, elapsed

        # Test SEQUENTIAL export first (baseline)
        seq_exported = 0
        for table_name in TABLES:
            success, _, _elapsed = _export_and_upload_table(
                table_name, con, output_dir, _dry_run=True
            )
            if success:
                seq_exported += 1
        assert seq_exported > 0, "Sequential export should export at least one table"

        # Clean output dir for parallel test
        for f in output_dir.glob("*.parquet"):
            f.unlink()

        # Test PARALLEL export
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(
                    _export_and_upload_table, table_name, con, output_dir, _dry_run=True
                )
                for table_name in TABLES
            ]
            par_exported = 0
            for future in futures:
                success, _, _ = future.result()
                if success:
                    par_exported += 1
        par_time = time.time() - start_time

        assert par_exported == seq_exported, (
            f"Parallel export ({par_exported}) should match sequential ({seq_exported})"
        )
        assert par_time > 0, "Parallel export time should be positive"
