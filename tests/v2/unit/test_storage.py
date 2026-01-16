"""Unit tests for the storage layer."""

from pathlib import Path

import ibis
from ibis.backends.duckdb import Backend
import pytest
from causaganha.v2.analysis.models import DecisionAnalysis
from causaganha.v2.api.client import Intimation, DestinarioAdvogado, LawyerInfo
from causaganha.v2.storage.connection import get_connection
from causaganha.v2.storage.queries import (
    store_intimations,
    store_lawyer_associations,
    get_unanalyzed_intimations,
    store_analysis,
    mark_as_analyzed,
    get_unrated_analyses,
    get_lawyer_rating,
    update_lawyer_rating,
    mark_analysis_as_rated,
    get_lawyer_name,
)


def test_get_connection_creates_db_file(tmp_path: Path) -> None:
    """Test that get_connection creates the database file if it doesn't exist."""
    db_path = tmp_path / "test.duckdb"
    assert not db_path.exists()

    con = get_connection(str(db_path))

    assert db_path.exists()
    assert isinstance(con, ibis.backends.duckdb.Backend)


def test_get_connection_singleton(tmp_path: Path) -> None:
    """Test that get_connection returns the same connection instance."""
    db_path = tmp_path / "test.duckdb"
    con1 = get_connection(str(db_path))
    con2 = get_connection(str(db_path))

    assert con1 is con2


def test_store_intimations(db_connection: Backend) -> None:
    """Test storing intimations."""
    # Mock intimation data
    intimations = [
        {
            "id": 1,
            "numero_processo": "1234567-89.2024.8.22.0001",
            "numeroprocessocommascara": "1234567-89.2024.8.22.0001",
            "data_disponibilizacao": "2024-01-01",
            "siglaTribunal": "TJRO",
            "idOrgao": 1,
            "tipoComunicacao": "Intimação",
            "nomeOrgao": "Vara Cível",
            "texto": "Texto da intimação",
            "link": "http://example.com/1",
            "tipoDocumento": "Despacho",
            "nomeClasse": "Procedimento Comum",
            "codigoClasse": "123",
            "hash": "hash1",
            "status": "P",
        },
    ]

    intimation_objects = [Intimation(**i) for i in intimations]

    count = store_intimations(db_connection, intimation_objects)
    assert count == 1

    # Verify data in DB
    t = db_connection.table("intimations")
    result = t.execute()
    assert len(result) == 1
    assert result.iloc[0]["id"] == 1
    assert result.iloc[0]["sigla_tribunal"] == "TJRO"


def test_store_intimations_updates_on_conflict(db_connection: Backend) -> None:
    """Test that storing an existing intimation updates it."""
    intimation1 = Intimation(
        id=1,
        siglaTribunal="TJRO",
        numero_processo="123",
        data_disponibilizacao="2024-01-01",
        texto="Original text",
    )
    store_intimations(db_connection, [intimation1])

    intimation2 = Intimation(
        id=1,
        siglaTribunal="TJRO",
        numero_processo="123",
        data_disponibilizacao="2024-01-01",
        texto="Updated text",
    )
    store_intimations(db_connection, [intimation2])

    t = db_connection.table("intimations")
    result = t.execute()
    assert len(result) == 1
    assert result.iloc[0]["texto"] == "Updated text"


def test_store_lawyer_associations(db_connection: Backend) -> None:
    """Test storing lawyer associations."""
    # Need an intimation first
    intimation = Intimation(
        id=1,
        siglaTribunal="TJRO",
        numero_processo="123",
        data_disponibilizacao="2024-01-01",
    )
    store_intimations(db_connection, [intimation])

    lawyers = [
        DestinarioAdvogado(
            advogado=LawyerInfo(
                id=1,
                nome="Advogado Teste",
                numero_oab="12345",
                uf_oab="RO"
            )
        )
    ]

    count = store_lawyer_associations(db_connection, 1, lawyers)
    assert count == 1

    # Verify DB
    t = db_connection.table("intimation_lawyers")
    result = t.execute()
    assert len(result) == 1
    assert result.iloc[0]["lawyer_name"] == "Advogado Teste"
    assert result.iloc[0]["oab_number"] == "12345"


def test_get_unanalyzed_intimations(db_connection: Backend) -> None:
    """Test getting unanalyzed intimations."""
    # Insert intimations directly via store_intimations
    intimation1 = Intimation(
        id=1,
        siglaTribunal="TJRO",
        numero_processo="123",
        data_disponibilizacao="2024-01-02",
        link="http://example.com/1",
    )
    intimation2 = Intimation(
        id=2,
        siglaTribunal="TJRO",
        numero_processo="124",
        data_disponibilizacao="2024-01-01",
        link="http://example.com/2",
    )
    # Intimation 3 has no link, should be ignored
    intimation3 = Intimation(
        id=3,
        siglaTribunal="TJRO",
        numero_processo="125",
        data_disponibilizacao="2024-01-03",
    )

    store_intimations(db_connection, [intimation1, intimation2, intimation3])

    # Mark intimation 2 as analyzed manually to test filtering
    db_connection.con.execute("UPDATE intimations SET analyzed = TRUE WHERE id = 2")

    pending = get_unanalyzed_intimations(db_connection, limit=10)

    # Should only return intimation 1 (has link, not analyzed)
    assert len(pending) == 1
    assert pending[0]["id"] == 1


def test_store_analysis(db_connection: Backend) -> None:
    """Test storing analysis results."""
    # Ensure intimation exists
    intimation = Intimation(
        id=1,
        siglaTribunal="TJRO",
        numero_processo="123",
        data_disponibilizacao="2024-01-01",
    )
    store_intimations(db_connection, [intimation])

    analysis = DecisionAnalysis(
        winner_lawyer_oab="1234",
        winner_lawyer_state="RO",
        winner_party_name="Winner",
        loser_lawyer_oab="5678",
        loser_lawyer_state="RO",
        loser_party_name="Loser",
        decision_type="sentença",
        outcome="procedente",
        judge_name="Judge",
        decision_reasoning="Reasoning",
        confidence_score=0.9,
    )

    store_analysis(db_connection, 1, analysis)

    # Verify DB
    t = db_connection.table("decision_analysis")
    result = t.execute()
    assert len(result) == 1
    assert result.iloc[0]["intimation_id"] == 1
    assert result.iloc[0]["outcome"] == "procedente"


def test_mark_as_analyzed(db_connection: Backend) -> None:
    """Test marking intimation as analyzed."""
    intimation = Intimation(
        id=1,
        siglaTribunal="TJRO",
        numero_processo="123",
        data_disponibilizacao="2024-01-01",
    )
    store_intimations(db_connection, [intimation])

    # Mark success
    mark_as_analyzed(db_connection, 1, success=True)

    t = db_connection.table("intimations")
    result = t.execute()
    assert result.iloc[0]["analyzed"]
    assert result.iloc[0]["analyzed_at"] is not None

    # Mark failure
    mark_as_analyzed(db_connection, 1, success=False, error="Error")

    result = t.execute()
    assert not result.iloc[0]["analyzed"]  # Should be False or 0
    assert result.iloc[0]["analysis_error"] == "Error"


def test_rating_queries(db_connection: Backend) -> None:
    """Test queries for rating pipeline."""
    # 1. Test get_unrated_analyses
    # Need to setup data
    db_connection.con.execute(
        "INSERT INTO intimations (id, numero_processo, data_disponibilizacao, sigla_tribunal) VALUES (1, '123', '2024-01-01', 'TJRO')"
    )
    # Use store_analysis which defaults rated=FALSE (via schema default if not set)
    analysis = DecisionAnalysis(
        winner_lawyer_oab="5733",
        winner_lawyer_state="RO",
        winner_party_name="Winner",
        loser_lawyer_oab="1234",
        loser_lawyer_state="RO",
        loser_party_name="Loser",
        decision_type="sentença",
        outcome="procedente",
        judge_name="Judge",
        decision_reasoning="Reasoning",
        confidence_score=0.9,
    )
    store_analysis(db_connection, 1, analysis)

    unrated = get_unrated_analyses(db_connection)
    assert len(unrated) == 1
    assert unrated[0]["intimation_id"] == 1

    # 2. Test update_lawyer_rating
    update_lawyer_rating(
        db_connection,
        oab_number="5733",
        oab_state="RO",
        lawyer_name="Winner",
        mu=26.0,
        sigma=8.0,
        wins=1,
        losses=0
    )

    # 3. Test get_lawyer_rating
    rating = get_lawyer_rating(db_connection, "5733", "RO")
    assert rating is not None
    assert rating["mu"] == 26.0
    assert rating["wins"] == 1
    assert rating["tribunal"] == "GLOBAL"

    # 4. Test mark_analysis_as_rated
    mark_analysis_as_rated(db_connection, unrated[0]["id"])

    unrated_after = get_unrated_analyses(db_connection)
    assert len(unrated_after) == 0


def test_update_lawyer_rating_global_upsert(db_connection: Backend) -> None:
    """Test that updating rating with default tribunal (GLOBAL) updates existing record."""
    # Insert initial rating
    update_lawyer_rating(
        db_connection,
        oab_number="9999",
        oab_state="RO",
        lawyer_name="Test Lawyer",
        mu=25.0,
        sigma=8.333,
        wins=0,
        losses=0
    )

    # Verify insert
    ratings = db_connection.table("lawyer_ratings").execute()
    assert len(ratings) == 1
    assert ratings.iloc[0]["mu"] == 25.0

    # Update rating (same OAB, same GLOBAL default)
    update_lawyer_rating(
        db_connection,
        oab_number="9999",
        oab_state="RO",
        lawyer_name="Test Lawyer",
        mu=26.0,
        sigma=8.0,
        wins=1,
        losses=0
    )

    # Verify update (should still be 1 record)
    ratings = db_connection.table("lawyer_ratings").execute()
    assert len(ratings) == 1
    assert ratings.iloc[0]["mu"] == 26.0
    assert ratings.iloc[0]["wins"] == 1
    assert ratings.iloc[0]["tribunal"] == "GLOBAL"

    # Test getting lawyer name
    name = get_lawyer_name(db_connection, "9999", "RO")
    # Should be None because we didn't insert into intimation_lawyers
    assert name is None

    # Insert association
    db_connection.con.execute(
        "INSERT INTO intimations (id, numero_processo, data_disponibilizacao, sigla_tribunal) VALUES (999, '999', '2024-01-01', 'TJRO')"
    )
    db_connection.con.execute(
        "INSERT INTO intimation_lawyers (intimation_id, oab_number, oab_state, lawyer_name) VALUES (999, '9999', 'RO', 'Stored Name')"
    )
    name = get_lawyer_name(db_connection, "9999", "RO")
    assert name == "Stored Name"
