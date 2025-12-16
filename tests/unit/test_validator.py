import pytest
import ibis
from causaganha.validation.validator import DataValidator
from causaganha.storage.schema import create_schema

@pytest.fixture
def con():
    """Create an in-memory DuckDB connection with schema."""
    conn = ibis.duckdb.connect(":memory:")
    create_schema(conn)
    return conn

def test_check_intimations_valid(con):
    """Test that valid intimations pass validation."""
    # Insert valid intimation
    t = con.table("intimations")
    # Need to match schema exactly or use helper.
    # Using raw sql for setup simplicity in tests is sometimes easier, but Ibis insert is preferred if possible.
    # However, Ibis insert from memtable is clean.

    data = [{
        "id": 1,
        "numero_processo": "1234567-89.2023.8.26.0000",
        "data_disponibilizacao": "2023-10-27",
        "sigla_tribunal": "TJSP",
        "tipo_comunicacao": "Intimação",
        "nome_orgao": "Vara 1",
        "texto": "Some text",
        "link": "https://example.com/doc",
        "tipo_documento": "Despacho",
        "nome_classe": "Procedimento",
        "codigo_classe": "123",
        "hash": "abc",
        "status": "pending",
        "ia_url": None,
        "archived_at": None
    }]
    con.insert("intimations", data)

    validator = DataValidator(con)
    report = validator.check_intimations()
    assert report["total_checked"] == 1
    assert report["invalid_links"] == 0
    assert report["missing_tribunal"] == 0

def test_check_intimations_invalid(con):
    """Test that invalid intimations are detected."""
    data = [
        {
            "id": 1,
            "numero_processo": "123",
            "data_disponibilizacao": "2023-10-27",
            "sigla_tribunal": None, # Missing tribunal
            "tipo_comunicacao": "Intimação",
            "nome_orgao": "Vara 1",
            "texto": "Some text",
            "link": "invalid-url", # Invalid link
            "tipo_documento": "Despacho",
            "nome_classe": "Procedimento",
            "codigo_classe": "123",
            "hash": "abc",
            "status": "pending",
            "ia_url": None,
            "archived_at": None
        }
    ]
    con.insert("intimations", data)

    validator = DataValidator(con)
    report = validator.check_intimations()
    assert report["total_checked"] == 1
    assert report["invalid_links"] == 1
    assert report["missing_tribunal"] == 1

def test_check_orphaned_analysis(con):
    """Test detection of orphaned analysis results."""
    # Insert analysis without corresponding intimation
    analysis_data = [{
        "id": 1,
        "intimation_id": 999, # Doesn't exist
        "outcome": "WIN",
        "summary": "Summary",
        "judge_name": "Judge",
        "confidence_score": 0.9,
        "analyzed_at": None,
        "winner_lawyer_oab": None,
        "winner_lawyer_state": None,
        "winner_party_name": None,
        "loser_lawyer_oab": None,
        "loser_lawyer_state": None,
        "loser_party_name": None,
        "decision_type": None,
        "decision_reasoning": None,
        "scored": False
    }]
    con.insert("analysis_results", analysis_data)

    validator = DataValidator(con)
    orphans = validator.check_orphaned_analysis()
    assert len(orphans) == 1
    assert orphans[0] == 1 # Analysis ID

def test_check_ratings_integrity(con):
    """Test validation of ratings values."""
    data = [
        {
            "oab_number": "123",
            "oab_state": "SP",
            "lawyer_name": "Test Lawyer",
            "mu": 25.0,
            "sigma": -1.0, # Invalid sigma
            "last_updated": None,
            "total_cases": 1,
            "wins": 1,
            "losses": 0
        }
    ]
    con.insert("lawyer_ratings", data)

    validator = DataValidator(con)
    report = validator.check_ratings()
    assert report["invalid_sigma"] == 1
