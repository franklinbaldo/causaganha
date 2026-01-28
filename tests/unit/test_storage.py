"""Storage unit tests."""

from dataclasses import dataclass

import ibis
import pandas as pd
import pytest
from ibis.backends.duckdb import Backend

from causaganha.analysis.models import DecisionAnalysis, DecisionType, Outcome
from causaganha.storage.connection import _initialize_schema
from causaganha.storage.repositories.analysis import (
    get_unrated_analyses,
    mark_analysis_as_rated,
    store_analysis,
)
from causaganha.storage.repositories.intimation import (
    get_lawyer_name,
    get_unanalyzed_intimations,
    get_unarchived_intimations,
    mark_as_analyzed,
    mark_as_archived,
    store_intimations,
    store_lawyer_associations,
)
from causaganha.storage.repositories.rating import (
    get_lawyer_rating,
    update_lawyer_rating,
)


@dataclass
class MockLawyer:
    """Mock lawyer data."""

    numero_oab: str
    uf_oab: str
    nome: str


@dataclass
class MockLawyerWrapper:
    """Mock lawyer wrapper."""

    advogado: MockLawyer


@dataclass
class MockIntimation:
    """Mock intimation data."""

    id: int
    numero_processo: str
    data_disponibilizacao: str
    sigla_tribunal: str
    id_orgao: int = 1
    tipo_comunicacao: str = "Intimação"
    nome_orgao: str = "Vara Cível"
    texto: str = "Teor do ato"
    link: str = "http://example.com/doc"
    tipo_documento: str = "Despacho"
    nome_classe: str = "Procedimento Comum"
    codigo_classe: str = "7"
    hash: str = "abc123hash"
    status: str = "A"
    ia_url: str | None = None


@pytest.fixture
def con() -> Backend:
    """Create in-memory DuckDB connection with schema."""
    conn = ibis.duckdb.connect(":memory:")
    _initialize_schema(conn)
    return conn


def test_store_intimations(con: Backend) -> None:
    """Test storing intimations."""
    intimation_id = 12345
    intimation = MockIntimation(
        id=intimation_id,
        numero_processo="1234567-89.2024.8.26.0000",
        data_disponibilizacao="2024-01-01",
        sigla_tribunal="TJSP",
        hash="hash1",
    )

    count = store_intimations(con, [intimation])
    assert count == 1

    # Verify insertion
    t = con.table("intimations")
    res = t.filter(t.id == intimation_id).to_pandas()
    assert len(res) == 1
    assert res.iloc[0]["sigla_tribunal"] == "TJSP"

    # Test Idempotency / Update
    intimation.texto = "Updated text"
    count = store_intimations(con, [intimation])
    assert count == 1

    res = t.filter(t.id == intimation_id).to_pandas()
    assert res.iloc[0]["texto"] == "Updated text"


def test_store_lawyer_associations(con: Backend) -> None:
    """Test storing lawyer associations."""
    intimation_id = 12345
    lawyer_data = MockLawyerWrapper(
        advogado=MockLawyer(numero_oab="123", uf_oab="SP", nome="Dr. Test"),
    )

    count = store_lawyer_associations(con, intimation_id, [lawyer_data])
    assert count == 1

    t = con.table("intimation_lawyers")
    res = t.filter(t.intimation_id == intimation_id).to_pandas()
    assert len(res) == 1
    assert res.iloc[0]["lawyer_name"] == "Dr. Test"

    count_2 = store_lawyer_associations(con, intimation_id, [lawyer_data])
    assert count_2 == 1


def test_store_lawyer_associations_batch(con: Backend) -> None:
    """Test storing lawyer associations in batch."""
    intimation_1 = 1
    intimation_2 = 2
    lawyer_1 = MockLawyerWrapper(
        advogado=MockLawyer(numero_oab="111", uf_oab="SP", nome="Lawyer 1"),
    )
    lawyer_2 = MockLawyerWrapper(
        advogado=MockLawyer(numero_oab="222", uf_oab="SP", nome="Lawyer 2"),
    )

    items = [
        (intimation_1, [lawyer_1]),
        (intimation_2, [lawyer_2]),
    ]

    from causaganha.storage.repositories.intimation import (
        store_lawyer_associations_batch,
    )

    count = store_lawyer_associations_batch(con, items)
    assert count == 2

    t = con.table("intimation_lawyers")
    res = t.filter(t.intimation_id.isin([intimation_1, intimation_2])).to_pandas()
    assert len(res) == 2


def test_get_lawyer_name(con: Backend) -> None:
    """Test getting lawyer name."""
    intimation_id = 111
    lawyer_data = MockLawyerWrapper(
        advogado=MockLawyer(numero_oab="999", uf_oab="RO", nome="Found Me"),
    )
    store_lawyer_associations(con, intimation_id, [lawyer_data])

    name = get_lawyer_name(con, "999", "RO")
    assert name == "Found Me"

    assert get_lawyer_name(con, "000", "XX") is None


def test_get_unanalyzed_intimations(con: Backend) -> None:
    """Test getting unanalyzed intimations."""
    # Insert one analyzed and one unanalyzed
    con.raw_sql("""
        INSERT INTO intimations (
            id, numero_processo, data_disponibilizacao,
            sigla_tribunal, analyzed, link
        )
        VALUES
        (1, 'proc1', '2024-01-01', 'TJRO', FALSE, 'http://link1'),
        (2, 'proc2', '2024-01-02', 'TJRO', TRUE, 'http://link2'),
        (3, 'proc3', '2024-01-03', 'TJRO', FALSE, NULL)
    """)

    results = get_unanalyzed_intimations(con)
    assert len(results) == 1
    assert results[0]["id"] == 1


def test_mark_as_analyzed(con: Backend) -> None:
    """Test marking as analyzed."""
    success_id = 10
    fail_id = 20

    con.raw_sql("""
        INSERT INTO intimations (
            id, numero_processo, data_disponibilizacao,
            sigla_tribunal, analyzed
        )
        VALUES (10, 'proc10', '2024-01-01', 'TJRO', FALSE)
    """)

    mark_as_analyzed(con, success_id, success=True)

    t = con.table("intimations")
    row = t.filter(t.id == success_id).to_pandas().iloc[0]
    # Check for bool explicitly as numpy/pandas might use different types
    assert bool(row["analyzed"]) is True
    assert not pd.isna(row["analyzed_at"])
    assert pd.isna(row["analysis_error"]) or row["analysis_error"] is None

    # Test failure case
    con.raw_sql("""
        INSERT INTO intimations (
            id, numero_processo, data_disponibilizacao,
            sigla_tribunal, analyzed
        )
        VALUES (20, 'proc20', '2024-01-01', 'TJRO', FALSE)
    """)

    mark_as_analyzed(con, fail_id, success=False, error="timeout")

    row = t.filter(t.id == fail_id).to_pandas().iloc[0]
    assert bool(row["analyzed"]) is False
    assert pd.isna(row["analyzed_at"])
    assert row["analysis_error"] == "timeout"


def test_store_analysis(con: Backend) -> None:
    """Test storing analysis."""
    intimation_id = 100
    expected_confidence = 0.95
    analysis = DecisionAnalysis(
        intimation_id=intimation_id,
        winner_lawyer_oab="12345",
        winner_lawyer_state="SP",
        loser_lawyer_oab="67890",
        loser_lawyer_state="SP",
        decision_type=DecisionType.SENTENCA,
        outcome=Outcome.PROCEDENTE,
        confidence_score=expected_confidence,
        analysis_method="llm",
    )

    store_analysis(con, intimation_id, analysis)

    t = con.table("decision_analysis")
    res = t.filter(t.intimation_id == intimation_id).to_pandas()
    assert len(res) == 1
    assert res.iloc[0]["outcome"] == "procedente"
    assert res.iloc[0]["confidence_score"] == expected_confidence


def test_get_unrated_analyses(con: Backend) -> None:
    """Test getting unrated analyses."""
    intimation_id = 200
    # Use store_analysis to insert data correctly
    analysis = DecisionAnalysis(
        intimation_id=intimation_id,
        winner_lawyer_oab="12345",
        winner_lawyer_state="SP",
        loser_lawyer_oab="67890",
        loser_lawyer_state="SP",
        decision_type=DecisionType.SENTENCA,
        outcome=Outcome.PROCEDENTE,
        confidence_score=0.9,
    )
    store_analysis(con, intimation_id, analysis)

    # Verify it is unrated by default
    res = get_unrated_analyses(con)
    assert len(res) == 1
    assert res[0]["intimation_id"] == intimation_id


def test_mark_analysis_as_rated(con: Backend) -> None:
    """Test marking analysis as rated."""
    intimation_id = 300
    analysis = DecisionAnalysis(
        intimation_id=intimation_id,
        winner_lawyer_oab="12345",
        winner_lawyer_state="SP",
        loser_lawyer_oab="67890",
        loser_lawyer_state="SP",
        decision_type=DecisionType.SENTENCA,
        outcome=Outcome.PROCEDENTE,
        confidence_score=0.9,
    )
    store_analysis(con, intimation_id, analysis)

    # Get the UUID generated
    t = con.table("decision_analysis")
    row = t.filter(t.intimation_id == intimation_id).to_pandas().iloc[0]
    analysis_id = row["id"]

    mark_analysis_as_rated(con, analysis_id)

    # Check
    row_after = t.filter(t.id == analysis_id).to_pandas().iloc[0]
    assert bool(row_after["rated"]) is True


def test_lawyer_rating_crud(con: Backend) -> None:
    """Test lawyer rating CRUD."""
    initial_mu = 30.0
    initial_wins = 10
    updated_mu = 32.0
    updated_wins = 11

    # Test update (insert)
    update_lawyer_rating(
        con, "123", "SP", "Dr. Winner",
        mu=initial_mu, sigma=5.0, wins=initial_wins, losses=2,
    )

    rating = get_lawyer_rating(con, "123", "SP")
    assert rating is not None
    assert rating["mu"] == initial_mu
    assert rating["wins"] == initial_wins

    # Test update (update)
    update_lawyer_rating(
        con, "123", "SP", "Dr. Winner",
        mu=updated_mu, sigma=4.0, wins=updated_wins, losses=2,
    )

    rating = get_lawyer_rating(con, "123", "SP")
    assert rating is not None
    assert rating["mu"] == updated_mu
    assert rating["wins"] == updated_wins

    # Test not found
    assert get_lawyer_rating(con, "999", "XX") is None


def test_archive_functions(con: Backend) -> None:
    """Test archive functions."""
    # Setup data
    con.raw_sql("""
        INSERT INTO intimations (
            id, numero_processo, data_disponibilizacao,
            sigla_tribunal, link, ia_url
        )
        VALUES
        (1, 'p1', '2024-01-01', 'TJRO', 'http://link1', NULL),
        (2, 'p2', '2024-01-02', 'TJRO', 'http://link2', 'http://archive.org/item')
    """)

    unarchived = get_unarchived_intimations(con)
    assert len(unarchived) == 1
    assert unarchived[0]["id"] == 1

    mark_as_archived(con, 1, "http://archive.org/newitem")

    t = con.table("intimations")
    row = t.filter(t.id == 1).to_pandas().iloc[0]
    assert row["ia_url"] == "http://archive.org/newitem"

    unarchived_after = get_unarchived_intimations(con)
    assert len(unarchived_after) == 0
