"""Unit tests for storage repositories."""

from dataclasses import dataclass
from datetime import date
from unittest.mock import MagicMock

import pytest

from causaganha.analysis.models import DecisionAnalysis, DecisionType, Outcome
from causaganha.storage.repositories import (
    mark_analysis_as_rated,
    mark_as_analyzed,
    mark_as_archived,
    store_analysis,
    store_intimations,
    store_lawyer_associations,
    update_lawyer_rating,
)


# Mock Intimation Model matching what's used in queries.py
@dataclass
class MockIntimation:
    """Mock intimation object."""

    id: int
    numero_processo: str
    data_disponibilizacao: date
    sigla_tribunal: str
    id_orgao: str
    tipo_comunicacao: str
    nome_orgao: str
    texto: str
    link: str
    tipo_documento: str
    nome_classe: str
    codigo_classe: str
    hash: str
    status: str

@dataclass
class MockLawyer:
    """Mock lawyer object."""

    numero_oab: str
    uf_oab: str
    nome: str

@dataclass
class MockLawyerInfo:
    """Mock lawyer info object."""

    advogado: MockLawyer

TEST_ID = 123
TEST_MU = 25.0

@pytest.fixture
def mock_backend() -> MagicMock:
    """Mock ibis backend."""
    backend = MagicMock()
    # Mock the raw duckdb connection
    backend.con = MagicMock()
    # Mock table() return for query building
    table_mock = MagicMock()
    backend.table.return_value = table_mock
    return backend

def test_store_intimations(mock_backend: MagicMock) -> None:
    """Test storing intimations."""
    intimation = MockIntimation(
        id=TEST_ID,
        numero_processo="1234567-89.2023.8.22.0001",
        data_disponibilizacao=date(2023, 5, 20),
        sigla_tribunal="TJRO",
        id_orgao="1",
        tipo_comunicacao="INTIMACAO",
        nome_orgao="Vara Cível",
        texto="Decisão proferida...",
        link="http://example.com/doc.pdf",
        tipo_documento="DESPACHO",
        nome_classe="PROCEDIMENTO COMUM",
        codigo_classe="7",
        hash="abc123hash",
        status="PENDING",
    )

    result = store_intimations(mock_backend, [intimation])

    assert result == 1
    mock_backend.con.execute.assert_called_once()
    args, _ = mock_backend.con.execute.call_args
    assert "INSERT INTO intimations" in args[0]
    assert args[1][0] == TEST_ID  # id

def test_store_lawyer_associations(mock_backend: MagicMock) -> None:
    """Test storing lawyer associations."""
    lawyer = MockLawyer(numero_oab="12345", uf_oab="RO", nome="Dr. Teste")
    lawyer_info = MockLawyerInfo(advogado=lawyer)

    result = store_lawyer_associations(mock_backend, TEST_ID, [lawyer_info])

    assert result == 1
    mock_backend.con.execute.assert_called_once()
    args, _ = mock_backend.con.execute.call_args
    assert "INSERT INTO intimation_lawyers" in args[0]
    assert args[1] == [TEST_ID, "12345", "RO", "Dr. Teste"]

def test_store_analysis(mock_backend: MagicMock) -> None:
    """Test storing analysis."""
    analysis = DecisionAnalysis(
        intimation_id=TEST_ID,
        decision_type=DecisionType.SENTENCA,
        outcome=Outcome.PROCEDENTE,
        confidence_score=0.95,
        analysis_method="llm",
        winner_lawyer_oab="12345",
        winner_lawyer_state="RO",
        winner_party_name="Party A",
    )

    store_analysis(mock_backend, TEST_ID, analysis)

    mock_backend.con.execute.assert_called_once()
    args, _ = mock_backend.con.execute.call_args
    assert "INSERT INTO decision_analysis" in args[0]
    # Check some parameters
    assert args[1][0] == TEST_ID # intimation_id
    assert args[1][1] == "12345" # winner_oab
    assert args[1][12] == "llm" # method

def test_mark_as_analyzed_success(mock_backend: MagicMock) -> None:
    """Test marking as analyzed success."""
    mark_as_analyzed(mock_backend, TEST_ID, success=True)

    mock_backend.con.execute.assert_called_once()
    args, _ = mock_backend.con.execute.call_args
    assert "UPDATE intimations" in args[0]
    assert "analyzed = TRUE" in args[0]
    assert args[1] == [TEST_ID]

def test_mark_as_analyzed_failure(mock_backend: MagicMock) -> None:
    """Test marking as analyzed failure."""
    mark_as_analyzed(mock_backend, TEST_ID, success=False, error="Some error")

    mock_backend.con.execute.assert_called_once()
    args, _ = mock_backend.con.execute.call_args
    assert "UPDATE intimations" in args[0]
    assert "analyzed = FALSE" in args[0]
    assert args[1] == ["Some error", TEST_ID]

def test_update_lawyer_rating(mock_backend: MagicMock) -> None:
    """Test updating lawyer rating."""
    update_lawyer_rating(
        mock_backend,
        oab_number="12345",
        oab_state="RO",
        lawyer_name="Dr. Teste",
        mu=TEST_MU,
        sigma=8.333,
        wins=1,
        losses=0,
    )

    mock_backend.con.execute.assert_called_once()
    args, _ = mock_backend.con.execute.call_args
    assert "INSERT INTO lawyer_ratings" in args[0]
    assert args[1][0] == "12345"
    assert args[1][3] == TEST_MU

def test_mark_analysis_as_rated(mock_backend: MagicMock) -> None:
    """Test marking analysis as rated."""
    mark_analysis_as_rated(mock_backend, "some-uuid")

    mock_backend.con.execute.assert_called_once()
    args, _ = mock_backend.con.execute.call_args
    assert "UPDATE decision_analysis" in args[0]
    assert "rated = TRUE" in args[0]
    assert args[1] == ["some-uuid"]

def test_mark_as_archived(mock_backend: MagicMock) -> None:
    """Test marking as archived."""
    mark_as_archived(mock_backend, TEST_ID, "https://archive.org/details/test")

    mock_backend.con.execute.assert_called_once()
    args, _ = mock_backend.con.execute.call_args
    assert "UPDATE intimations" in args[0]
    assert "ia_url = ?" in args[0]
    assert args[1] == ["https://archive.org/details/test", TEST_ID]
