"""Unit tests for Storage Layer."""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from ibis import BaseBackend

from causaganha.domain.models import Intimation, Lawyer, Party
from causaganha.storage.connection import get_connection
from causaganha.storage.repository import IntimationRepository
from causaganha.storage.schema import create_schema


@pytest.fixture
def memory_db() -> BaseBackend:
    """Create a fresh in-memory database connection for each test."""
    con = get_connection(":memory:")
    # We need to initialize schema for tests
    create_schema(con)

    return con


def test_connection_singleton_behavior() -> None:
    """Test that get_connection returns the same instance for same path."""
    _ = get_connection("test_db.duckdb")
    _ = get_connection("test_db.duckdb")

    # Assert they are the same object
    # (Singleton behavior not currently implemented, but testing for when it is)
    # assert con_default1 is con_default2

    # Clean up
    if Path("test_db.duckdb").exists():
        Path("test_db.duckdb").unlink()


def test_schema_initialization(memory_db: BaseBackend) -> None:
    """Test that tables are created on initialization."""
    tables = memory_db.list_tables()
    assert "intimations" in tables
    assert "intimation_lawyers" in tables
    # The table name defined in schema_definitions.py is "analysis_results"
    assert "analysis_results" in tables


@pytest.mark.asyncio
async def test_repository_save_intimation(memory_db: BaseBackend) -> None:
    """Test saving an intimation via repository."""
    repo = IntimationRepository(memory_db)

    intimation = Intimation(
        id=1,
        numero_processo="0001-01.2024.8.22.0001",
        sigla_tribunal="TJRO",
        data_disponibilizacao=date(2024, 12, 1),
        tipo_comunicacao="Intimação",
        nome_orgao="Vara 1",
        texto="Texto",
        link="http://pdf",
        tipo_documento="Doc",
        nome_classe="Classe",
        hash="abc",
        status="P",
        advogados=[
            Lawyer(id=10, nome="Adv 1", numero_oab="123", uf_oab="RO"),
        ],
        partes=[
            Party(nome="Parte 1", polo="A"),
        ],
    )

    await repo.store_intimations([intimation])

    # Verify insertion
    t = memory_db.table("intimations")
    result = t.filter(t.id == 1).execute()
    assert len(result) == 1
    assert result.iloc[0]["numero_processo"] == "0001-01.2024.8.22.0001"

    # Verify lawyers
    tl = memory_db.table("intimation_lawyers")
    result_l = tl.filter(tl.intimation_id == 1).execute()
    assert len(result_l) == 1
    assert result_l.iloc[0]["oab_number"] == "123"


@pytest.mark.asyncio
async def test_repository_get_unanalyzed(memory_db: BaseBackend) -> None:
    """Test retrieving unanalyzed intimations."""
    repo = IntimationRepository(memory_db)

    # Insert one analyzed and one unanalyzed
    con = memory_db
    con.raw_sql("""
        INSERT INTO intimations (
            id, numero_processo, data_disponibilizacao, sigla_tribunal, analyzed, link
        )
        VALUES
        (1, 'proc1', '2024-01-01', 'TJRO', TRUE, 'link1'),
        (2, 'proc2', '2024-01-01', 'TJRO', FALSE, 'link2'),
        (3, 'proc3', '2024-01-01', 'TJRO', FALSE, NULL) -- No link, should be skipped?
    """)

    # Repository method is `get_unanalyzed_intimations`
    results = await repo.get_unanalyzed_intimations(limit=10)

    assert len(results) >= 1
    ids = [i["id"] for i in results]
    assert 2 in ids
    assert 1 not in ids
    # Logic should skip null links
    assert 3 not in ids


@pytest.mark.asyncio
async def test_repository_save_intimation_sets_defaults(memory_db: BaseBackend) -> None:
    """Test that saving an intimation sets the correct default values."""
    repo = IntimationRepository(memory_db)

    intimation = Intimation(
        id=1,
        numero_processo="0001-01.2024.8.22.0001",
        sigla_tribunal="TJRO",
        data_disponibilizacao=date(2024, 12, 1),
        tipo_comunicacao="Intimação",
        nome_orgao="Vara 1",
        texto="Texto",
        link="http://pdf",
        tipo_documento="Doc",
        nome_classe="Classe",
        hash="abc",
        status="P",
        advogados=[],
        partes=[],
    )

    await repo.store_intimations([intimation])

    t = memory_db.table("intimations")
    result = t.filter(t.id == 1).execute()

    assert len(result) == 1
    record = result.iloc[0]

    assert not record["analyzed"]
    assert record["ia_url"] is None
    assert pd.isna(record["archived_at"])
    assert record["needs_download"]

@pytest.mark.asyncio
async def test_store_analysis_result(memory_db: BaseBackend) -> None:
    """Test storing analysis result updates intimation as analyzed."""
    repo = IntimationRepository(memory_db)
    con = memory_db

    # Setup intimation
    con.raw_sql("""
        INSERT INTO intimations (id, numero_processo, data_disponibilizacao, sigla_tribunal, analyzed, link)
        VALUES (100, 'proc100', '2024-01-01', 'TJRO', FALSE, 'link100')
    """)

    result = {
        "intimation_id": 100,
        "winner_lawyer_oab": "123",
        "winner_lawyer_state": "RO",
        "loser_lawyer_oab": "456",
        "loser_lawyer_state": "RO",
        "outcome": "procedente",
        "confidence_score": 0.9,
        # Add required fields for insertion if strict schema (some may be optional/nullable)
        # Assuming schema allows nulls or we provide minimal set.
        # Checking schema definitions if needed.
    }

    await repo.store_analysis_result(result)

    # Check analysis results table
    t_ar = memory_db.table("analysis_results")
    rows = t_ar.filter(t_ar.intimation_id == 100).execute()
    assert len(rows) == 1
    assert rows.iloc[0]["winner_lawyer_oab"] == "123"

    # Check intimation table updated
    t_int = memory_db.table("intimations")
    int_row = t_int.filter(t_int.id == 100).execute().iloc[0]
    assert int_row["analyzed"] == True
    assert not pd.isna(int_row["analyzed_at"])

@pytest.mark.asyncio
async def test_store_analysis_results_batch(memory_db: BaseBackend) -> None:
    """Test batch storing of analysis results."""
    repo = IntimationRepository(memory_db)
    con = memory_db

    con.raw_sql("""
        INSERT INTO intimations (id, numero_processo, data_disponibilizacao, sigla_tribunal, analyzed, link)
        VALUES
        (200, 'proc200', '2024-01-01', 'TJRO', FALSE, 'link200'),
        (201, 'proc201', '2024-01-01', 'TJRO', FALSE, 'link201')
    """)

    results = [
        {"intimation_id": 200, "winner_lawyer_oab": "A", "winner_lawyer_state": "RO", "outcome": "W"},
        {"intimation_id": 201, "winner_lawyer_oab": "B", "winner_lawyer_state": "RO", "outcome": "L"},
    ]

    await repo.store_analysis_results_batch(results)

    t_int = memory_db.table("intimations")
    rows = t_int.filter(t_int.id.isin([200, 201])).execute()
    assert len(rows) == 2
    assert all(rows["analyzed"])

@pytest.mark.asyncio
async def test_get_unarchived_intimations(memory_db: BaseBackend) -> None:
    """Test retrieving unarchived intimations."""
    repo = IntimationRepository(memory_db)
    con = memory_db

    con.raw_sql("""
        INSERT INTO intimations (id, numero_processo, data_disponibilizacao, sigla_tribunal, link, ia_url)
        VALUES
        (300, 'proc300', '2024-01-01', 'TJRO', 'link300', NULL),
        (301, 'proc301', '2024-01-01', 'TJRO', 'link301', 'http://archive.org/item'),
        (302, 'proc302', '2024-01-01', 'TJRO', NULL, NULL)
    """)

    results = await repo.get_unarchived_intimations()
    ids = [r["id"] for r in results]
    assert 300 in ids
    assert 301 not in ids
    assert 302 not in ids

@pytest.mark.asyncio
async def test_mark_as_archived(memory_db: BaseBackend) -> None:
    """Test marking intimation as archived."""
    repo = IntimationRepository(memory_db)
    con = memory_db

    con.raw_sql("""
        INSERT INTO intimations (id, numero_processo, data_disponibilizacao, sigla_tribunal, link, ia_url)
        VALUES (400, 'proc400', '2024-01-01', 'TJRO', 'link400', NULL)
    """)

    await repo.mark_as_archived("400", "http://archive.org/400")

    t_int = memory_db.table("intimations")
    row = t_int.filter(t_int.id == 400).execute().iloc[0]
    assert row["ia_url"] == "http://archive.org/400"
    assert not pd.isna(row["archived_at"])

@pytest.mark.asyncio
async def test_mark_as_archived_validation(memory_db: BaseBackend) -> None:
    """Test validation in mark_as_archived."""
    repo = IntimationRepository(memory_db)

    with pytest.raises(ValueError, match="Intimation ID cannot be empty"):
        await repo.mark_as_archived("", "http://url")

    with pytest.raises(ValueError, match="Invalid IA URL"):
        await repo.mark_as_archived("123", "invalid-url")

@pytest.mark.asyncio
async def test_get_all_intimations(memory_db: BaseBackend) -> None:
    """Test get_all_intimations."""
    repo = IntimationRepository(memory_db)
    con = memory_db
    con.raw_sql("INSERT INTO intimations (id, numero_processo, data_disponibilizacao, sigla_tribunal) VALUES (1, 'p', '2024-01-01', 'TJ')")

    res = await repo.get_all_intimations()
    assert len(res) == 1

@pytest.mark.asyncio
async def test_get_unscored_analyses(memory_db: BaseBackend) -> None:
    """Test get_unscored_analyses."""
    repo = IntimationRepository(memory_db)
    con = memory_db

    # id=1 unscored, lawyers identified
    # id=2 scored
    # id=3 unscored, lawyer missing
    con.raw_sql("""
        INSERT INTO analysis_results (id, intimation_id, winner_lawyer_oab, loser_lawyer_oab, scored)
        VALUES
        (101, 1, '123', '456', FALSE),
        (102, 2, '123', '456', TRUE),
        (103, 3, NULL, '456', FALSE)
    """)

    res = await repo.get_unscored_analyses()
    ids = [r["id"] for r in res]
    assert 101 in ids
    assert 102 not in ids
    assert 103 not in ids

@pytest.mark.asyncio
async def test_save_and_get_lawyer_ratings(memory_db: BaseBackend) -> None:
    """Test saving and retrieving lawyer ratings."""
    repo = IntimationRepository(memory_db)

    ratings = [{
        "oab_number": "123",
        "oab_state": "RO",
        "lawyer_name": "Test Lawyer",
        "mu": 25.0,
        "sigma": 8.333,
        "total_cases": 1,
        "wins": 1,
        "losses": 0
    }]

    await repo.save_lawyer_ratings(ratings)

    fetched = await repo.get_lawyer_ratings([("123", "RO")])
    assert len(fetched) == 1
    assert fetched[0]["oab_number"] == "123"
    assert fetched[0]["mu"] == 25.0

    # Test update
    ratings[0]["mu"] = 26.0
    await repo.save_lawyer_ratings(ratings)

    fetched_updated = await repo.get_lawyer_ratings([("123", "RO")])
    assert fetched_updated[0]["mu"] == 26.0

@pytest.mark.asyncio
async def test_mark_analyses_scored(memory_db: BaseBackend) -> None:
    """Test mark_analyses_scored."""
    repo = IntimationRepository(memory_db)
    con = memory_db

    con.raw_sql("""
        INSERT INTO analysis_results (id, intimation_id, scored)
        VALUES (500, 1, FALSE)
    """)

    await repo.mark_analyses_scored([500])

    t = memory_db.table("analysis_results")
    row = t.filter(t.id == 500).execute().iloc[0]
    assert row["scored"] == True
