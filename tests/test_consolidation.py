"""Test parallel Parquet export with local ZIPs."""

import json
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import duckdb
import ibis
import pytest
import structlog

from scripts.pipeline.consolidate import (
    NAMESPACE_DJEN,
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
    """Verify all consolidated tables are produced from synthetic data."""
    con = ibis.duckdb.connect()
    init_tables(con)

    with tempfile.TemporaryDirectory() as tmpdir:
        ndjson_dir = Path(tmpdir)
        _create_synthetic_ndjson(ndjson_dir)

        counts = _load_and_transform(con, ndjson_dir, item_id="djen-tjsp-2026")

    # All tables should exist
    assert len(TABLES) == 9, f"Expected 9 tables, got {len(TABLES)}"

    # Core tables must have rows
    assert counts.get("comunicacoes", 0) > 0, "comunicacoes should have rows"
    assert counts.get("textos", 0) > 0, "textos should have rows"
    assert counts.get("advogados", 0) > 0, "advogados should have rows"
    assert counts.get("destinatarios", 0) > 0, "destinatarios should have rows"
    assert counts.get("processos", 0) > 0, "processos should have rows"


def test_classificacoes_removed_from_schema():
    """Classification is still under development — it must not be a consolidated table."""
    assert "classificacoes" not in TABLES
    assert "classificacoes" not in TABLE_SCHEMAS


def test_parquet_export_roundtrip():
    """Verify Parquet files can be created and read back with correct row counts."""
    con = ibis.duckdb.connect()
    init_tables(con)

    with tempfile.TemporaryDirectory() as tmpdir:
        ndjson_dir = Path(tmpdir) / "ndjson"
        ndjson_dir.mkdir()
        _create_synthetic_ndjson(ndjson_dir)
        _load_and_transform(con, ndjson_dir, item_id="djen-tjsp-2026")

        output_dir = Path(tmpdir) / "parquet"
        output_dir.mkdir()

        exported = 0
        for table_name in TABLES:
            t = con.table(table_name)
            count = t.count().execute()
            if count == 0:
                continue

            output_path = output_dir / f"{table_name}.parquet"
            con.raw_sql(f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
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


# ---------------------------------------------------------------------------
# Advogado schema stability: read_json_auto infers ``advogado`` as JSON (not
# STRUCT) when a partition mixes shapes.  The advogado tables must come out
# identical whichever type DuckDB picks, otherwise the same lawyer gets a
# different global UUID depending on the partition.
# ---------------------------------------------------------------------------

_ADV_TABLES = ("comunicacao_advogados", "advogados", "advogado_nomes")


def _adv_record(record_id: str, advogados: list[dict]) -> dict:
    return {
        "id": record_id,
        "texto": f"INTIMAÇÃO {record_id}",
        "numeroProcesso": "0000001-02.2022.8.22.0001",
        "dataDisponibilizacao": "2022-03-01",
        "destinatarios": [{"nome": "PARTE AUTORA", "polo": "Ativo"}],
        "destinatarioadvogados": [{"advogado": adv} for adv in advogados],
    }


_LAWYER_MARIA = {"nome": "DRA MARIA", "numeroOAB": "12345", "ufOAB": "RO", "id": 7}
_LAWYER_PEDRO = {"nome": "DR PEDRO", "numeroOAB": "67890", "ufOAB": "RO"}


# Third file per variant: (mixed lawyers, clean lawyers).  The mixed value forces
# the JSON inference; the clean value is what the same record looks like when
# every file agrees on the shape.  A bare string is treated as no advogado, the
# same as null.
_MIXED_THIRD_FILE = {
    "advogado_json": ([["NAO INFORMADO"]], [None]),
    "numero_oab_json": (
        [{**_LAWYER_PEDRO, "numeroOAB": 67890}],
        [_LAWYER_PEDRO],
    ),
}


def _advogado_fixture_files(variant: str, *, mixed: bool) -> dict[str, list[dict]]:
    """NDJSON files for one partition, with or without the forced-JSON record."""
    if variant not in _MIXED_THIRD_FILE:
        msg = f"unknown variant: {variant}"
        raise ValueError(msg)
    mixed_lawyers, clean_lawyers = _MIXED_THIRD_FILE[variant]
    third = mixed_lawyers if mixed else clean_lawyers
    return {
        "TJRO__djen-2022-03-01-TJRO.ndjson": [_adv_record("1001", [_LAWYER_MARIA])],
        "TJRO__djen-2022-03-02-TJRO.ndjson": [_adv_record("1002", [_LAWYER_PEDRO])],
        "TJRO__djen-2022-03-03-TJRO.ndjson": [_adv_record("1003", third)],
    }


def _write_partition(ndjson_dir: Path, files: dict[str, list[dict]]) -> None:
    for name, records in files.items():
        with (ndjson_dir / name).open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _inferred_destinatarioadvogados_type(ndjson_dir: Path) -> str:
    """DuckDB's inferred type for destinatarioadvogados (the list holding advogado)."""
    probe = duckdb.connect()
    probe.execute(
        f"CREATE TABLE probe AS SELECT * FROM read_json_auto('{ndjson_dir}/*.ndjson', "
        f"filename=true, union_by_name=true)",
    )
    rows = probe.sql(
        "SELECT column_type FROM (DESCRIBE probe) WHERE column_name = 'destinatarioadvogados'",
    ).fetchall()
    probe.close()
    return str(rows[0][0])


def _advogado_tables(variant: str, *, mixed: bool) -> tuple[str, dict[str, list[dict]]]:
    con = ibis.duckdb.connect()
    init_tables(con)
    with tempfile.TemporaryDirectory() as tmpdir:
        ndjson_dir = Path(tmpdir)
        _write_partition(ndjson_dir, _advogado_fixture_files(variant, mixed=mixed))
        inferred = _inferred_destinatarioadvogados_type(ndjson_dir)
        _load_and_transform(con, ndjson_dir, item_id="djen-tjro-2022")
    tables = {
        name: sorted(
            con.table(name).execute().to_dict("records"),
            key=lambda r: json.dumps(r, sort_keys=True, default=str),
        )
        for name in _ADV_TABLES
    }
    return inferred, tables


@pytest.mark.parametrize("variant", ["advogado_json", "numero_oab_json"])
def test_advogado_tables_identical_when_partition_infers_json(variant):
    """Mixed-shape partitions must produce the same advogado rows as STRUCT ones."""
    struct_type, struct_tables = _advogado_tables(variant, mixed=False)
    mixed_type, mixed_tables = _advogado_tables(variant, mixed=True)

    # The fixture must actually force the type under test, or the test proves nothing.
    assert "advogado STRUCT(" in struct_type, struct_type
    assert "JSON" not in struct_type, struct_type
    if variant == "advogado_json":
        assert "advogado JSON" in mixed_type, mixed_type
    else:
        assert "advogado STRUCT(" in mixed_type
        assert "numeroOAB JSON" in mixed_type, mixed_type

    assert mixed_tables == struct_tables

    # Values are unquoted text and the UUIDs use the OAB+UF key, not JSON text.
    maria_id = str(uuid.uuid5(NAMESPACE_DJEN, "12345:RO"))
    pedro_id = str(uuid.uuid5(NAMESPACE_DJEN, "67890:RO"))
    adv_ids = {row["id"] for row in mixed_tables["advogados"]}
    assert {maria_id, pedro_id} <= adv_ids
    maria = next(r for r in mixed_tables["advogados"] if r["id"] == maria_id)
    assert maria["numero_oab"] == "12345"
    assert maria["uf_oab"] == "RO"
    assert maria["nome"] == "DRA MARIA"
