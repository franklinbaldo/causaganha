import pytest
import json
import uuid
from pathlib import Path

# Add src to Python path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import CausaGanhaDB
from src.pii_manager import PiiManager # Needed to generate some UUIDs for testing

@pytest.fixture
def db_instance(temp_db: Path): # temp_db from conftest.py
    """Fixture to provide an initialized CausaGanhaDB instance for testing PII-related DB operations."""
    db = CausaGanhaDB(db_path=temp_db)
    db.connect() # Runs migrations
    yield db
    db.close()

@pytest.fixture
def pii_manager_for_test_db(db_instance: CausaGanhaDB):
    """Provides a PiiManager instance using the same DB connection as db_instance."""
    return PiiManager(db_instance.conn)


def test_add_raw_decision_basic(db_instance: CausaGanhaDB, pii_manager_for_test_db: PiiManager):
    """Test basic insertion of a PII-replaced decision."""

    # Generate some UUIDs for PII fields as if PiiManager had processed them
    case_no_uuid = pii_manager_for_test_db.get_or_create_pii_mapping("0000001-01.2023.8.22.0001", "CASE_NUMBER", "00000010120238220001")
    party_a1_uuid = pii_manager_for_test_db.get_or_create_pii_mapping("Parte Ativa Um", "PARTY_NAME", "parte ativa um")
    lawyer_a1_full_uuid = pii_manager_for_test_db.get_or_create_pii_mapping("Advogado Ativo Um (OAB/UF 111)", "LAWYER_FULL_STRING", "Advogado Ativo Um (OAB/UF 111)")
    # Ensure the normalized lawyer ID is also in the map for completeness, though not directly stored in this call's args
    _ = pii_manager_for_test_db.get_or_create_pii_mapping("advogado ativo um", "LAWYER_ID_NORMALIZED", "advogado ativo um")


    decision_params = {
        "numero_processo_uuid": case_no_uuid,
        "polo_ativo_uuids_json": json.dumps([party_a1_uuid]),
        "polo_passivo_uuids_json": json.dumps([pii_manager_for_test_db.get_or_create_pii_mapping("Parte Passiva Um", "PARTY_NAME", "parte passiva um")]),
        "advogados_polo_ativo_full_str_uuids_json": json.dumps([lawyer_a1_full_uuid]),
        "advogados_polo_passivo_full_str_uuids_json": json.dumps([
            pii_manager_for_test_db.get_or_create_pii_mapping("Advogado Passivo Um (OAB/UF 222)", "LAWYER_FULL_STRING", "Advogado Passivo Um (OAB/UF 222)")
        ]),
        "resultado_original": "Procedente",
        "data_decisao_original": "2023-10-26",
        "raw_json_pii_replaced": json.dumps({
            "numero_processo_uuid": case_no_uuid,
            "polo_ativo_uuids": [party_a1_uuid],
            # ... other PII-replaced fields in the raw JSON dump
        }),
        "json_source_file": "test_extraction.json",
        "tipo_decisao": "Sentença",
        "validation_status": "valid"
    }

    if dry_run_flag := False: # Placeholder if we want to test dry run logic if add_raw_decision supported it
        pass
    else:
        decision_id = db_instance.add_raw_decision(**decision_params)
        assert decision_id is not None
        assert decision_id > 0

        # Verify the data in the database
        fetched_row_tuple = db_instance.conn.execute("SELECT * FROM decisoes WHERE id = ?", (decision_id,)).fetchone()
        assert fetched_row_tuple is not None

        colnames = [desc[0] for desc in db_instance.conn.description]
        fetched_row = dict(zip(colnames, fetched_row_tuple))

        assert fetched_row["numero_processo"] == case_no_uuid
        assert json.loads(fetched_row["polo_ativo"]) == [party_a1_uuid]
        assert json.loads(fetched_row["advogados_polo_ativo"]) == [lawyer_a1_full_uuid]
        assert fetched_row["resultado"] == "Procedente"
        assert fetched_row["data_decisao"] is not None # DuckDB stores date as date object
        assert fetched_row["raw_json_data"] == decision_params["raw_json_pii_replaced"]
        assert fetched_row["json_source_file"] == "test_extraction.json"
        assert fetched_row["validation_status"] == "valid"

def test_add_raw_decision_minimal_params(db_instance: CausaGanhaDB, pii_manager_for_test_db: PiiManager):
    """Test adding a decision with only the essential PII-replaced fields."""
    case_no_uuid = pii_manager_for_test_db.get_or_create_pii_mapping("9999999-99.2023.8.22.9999", "CASE_NUMBER", "99999999920238229999")

    decision_params = {
        "numero_processo_uuid": case_no_uuid,
        "polo_ativo_uuids_json": json.dumps([]), # Empty list
        "polo_passivo_uuids_json": json.dumps([]),
        "advogados_polo_ativo_full_str_uuids_json": json.dumps([]),
        "advogados_polo_passivo_full_str_uuids_json": json.dumps([]),
        "resultado_original": "Extinto",
        "data_decisao_original": None, # Test optional date
        "raw_json_pii_replaced": json.dumps({"numero_processo_uuid": case_no_uuid, "minimal": True}),
    }

    decision_id = db_instance.add_raw_decision(**decision_params)
    assert decision_id is not None

    fetched_row = db_instance.conn.execute("SELECT numero_processo, resultado, data_decisao FROM decisoes WHERE id = ?", (decision_id,)).fetchone()
    assert fetched_row is not None
    assert fetched_row[0] == case_no_uuid
    assert fetched_row[1] == "Extinto"
    assert fetched_row[2] is None # data_decisao should be NULL

# To run these tests: pytest tests/test_database_pii.py
# Ensure conftest.py is in the tests/ directory or project root recognized by pytest
pytest.main(["-v", __file__]) # Optional: run tests if file is executed directly
