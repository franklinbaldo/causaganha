import pytest
import ibis
import datetime
from unittest.mock import MagicMock
from causaganha.storage.repositories.analysis import AnalysisRepository
from causaganha.storage.connection import get_connection
from causaganha.storage.schema import create_schema

@pytest.fixture
def memory_con():
    con = get_connection(":memory:")
    create_schema(con)
    return con

@pytest.fixture
def analysis_repo(memory_con):
    return AnalysisRepository(memory_con)

def test_store_analysis_result(analysis_repo):
    # Setup
    result = {
        "id": 12345,
        "intimation_id": 999,
        "winner_lawyer_oab": "123",
        "winner_lawyer_state": "RO",
        "scored": False,
        "analyzed_at": datetime.datetime.now()
    }

    # Create intimation
    con = analysis_repo.con
    con.raw_sql("INSERT INTO intimations (id, numero_processo, data_disponibilizacao, sigla_tribunal, analyzed) VALUES (999, '123', '2023-01-01', 'TJRO', FALSE)")

    analysis_repo._sync_store_analysis_result(result)

    # Verify analysis stored
    t_analysis = con.table("analysis_results")
    rows = t_analysis.execute().to_dict(orient="records")
    assert len(rows) == 1
    assert rows[0]["id"] == 12345

    # Verify intimation updated
    t_intimation = con.table("intimations")
    intimation = t_intimation.filter(t_intimation.id == 999).execute().to_dict(orient="records")[0]
    assert intimation["analyzed"] == True
    assert intimation["analyzed_at"] is not None

def test_store_analysis_results_batch(analysis_repo):
    con = analysis_repo.con
    con.raw_sql("INSERT INTO intimations (id, numero_processo, data_disponibilizacao, sigla_tribunal, analyzed) VALUES (1001, '1', '2023-01-01', 'TJRO', FALSE)")
    con.raw_sql("INSERT INTO intimations (id, numero_processo, data_disponibilizacao, sigla_tribunal, analyzed) VALUES (1002, '2', '2023-01-01', 'TJRO', FALSE)")

    results = [
        {"id": 1, "intimation_id": 1001, "winner_lawyer_oab": "A", "scored": False},
        {"id": 2, "intimation_id": 1002, "winner_lawyer_oab": "B", "scored": False},
    ]

    analysis_repo._sync_store_analysis_results_batch(results)

    # Verify analyses
    t_analysis = con.table("analysis_results")
    count = t_analysis.count().execute()
    assert count == 2

    # Verify intimations updated
    t_intimation = con.table("intimations")
    analyzed_count = t_intimation.filter(t_intimation.analyzed == True).count().execute()
    assert analyzed_count == 2

def test_get_unscored_analyses(analysis_repo):
    con = analysis_repo.con
    # Clear tables
    con.raw_sql("DELETE FROM analysis_results")

    # Insert test data. IDs must be int.
    # Using SQL to insert boolean and NULL properly
    con.raw_sql("""
        INSERT INTO analysis_results (id, winner_lawyer_oab, loser_lawyer_oab, scored)
        VALUES
        (1, 'A', 'B', FALSE),
        (2, 'C', 'D', NULL),
        (3, 'E', 'F', TRUE),
        (4, NULL, 'H', FALSE) -- Invalid, missing winner
    """)

    unscored = analysis_repo._sync_get_unscored_analyses(limit=10)

    ids = sorted([r["id"] for r in unscored])
    assert ids == [1, 2]

def test_mark_analyses_scored(analysis_repo):
    con = analysis_repo.con
    con.raw_sql("DELETE FROM analysis_results")
    con.raw_sql("INSERT INTO analysis_results (id, scored) VALUES (1, FALSE)")

    analysis_repo._sync_mark_analyses_scored([1])

    t_analysis = con.table("analysis_results")
    row = t_analysis.filter(t_analysis.id == 1).execute().to_dict(orient="records")[0]
    assert row["scored"] == True
