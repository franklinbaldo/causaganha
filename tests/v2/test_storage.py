from datetime import date

import ibis
import pytest

from causaganha.v2.api.models import DestinatarioAdvogado, Intimation, LawyerInfo
from causaganha.v2.storage.connection import get_connection, reset_connection
from causaganha.v2.storage.queries import (
    get_lawyer_stats,
    get_recent_analyses,
    get_unanalyzed_intimations,
    store_intimations,
    store_lawyer_associations,
)


def test_get_connection_in_memory():
    """Test connection to in-memory database"""
    reset_connection()
    con = get_connection(":memory:")
    assert con is not None
    # Schema should be initialized
    assert "intimations" in con.list_tables()


def test_singleton_behavior():
    """Test that get_connection returns the same instance"""
    reset_connection()
    con1 = get_connection(":memory:")
    con2 = get_connection(":memory:")
    assert con1 is con2


def test_schema_created():
    """Test that tables are created"""
    reset_connection()
    con = get_connection(":memory:")
    tables = con.list_tables()
    expected_tables = [
        "intimations",
        "intimation_lawyers",
        "decision_analysis",
        "lawyer_ratings",
        "sync_log",
        "monitored_courts",
    ]
    for table in expected_tables:
        assert table in tables


def test_store_intimations():
    """Test storing intimations in database"""
    reset_connection()
    con = get_connection(":memory:")

    # Create sample intimation
    intimation = Intimation(
        id=123456,
        numero_processo="0001234-56.2024.8.22.0001",
        data_disponibilizacao="2024-12-01",
        siglaTribunal="TJRO",
        tipoComunicacao="INTIMACAO",
        nomeOrgao="Vara Civel",
        texto="Decisao...",
        link="https://pje.tjro.jus.br/doc/12345.pdf",
        tipoDocumento="Despacho",
        nomeClasse="Procedimento Comum",
        hash="abc123hash",
        status="A",
    )

    # Store
    count = store_intimations(con, [intimation])
    assert count == 1

    # Verify
    t = con.table("intimations")
    res = t.filter(t.id == 123456).execute()
    assert len(res) == 1
    assert res.iloc[0]["numero_processo"] == "0001234-56.2024.8.22.0001"


def test_store_lawyer_associations():
    """Test storing lawyer associations"""
    reset_connection()
    con = get_connection(":memory:")

    # Insert intimation first (needed for FK)
    con.raw_sql(
        "INSERT INTO intimations (id, numero_processo, data_disponibilizacao, sigla_tribunal) VALUES (1, '123', '2024-01-01', 'TJRO')"
    )

    lawyers = [
        DestinatarioAdvogado(
            advogado=LawyerInfo(
                id=100, nome="John Doe", numero_oab="12345", uf_oab="RO"
            )
        )
    ]

    count = store_lawyer_associations(con, 1, lawyers)
    assert count == 1

    t = con.table("intimation_lawyers")
    res = t.execute()
    assert len(res) == 1
    assert res.iloc[0]["lawyer_name"] == "John Doe"


def test_get_unanalyzed_intimations():
    """Test fetching unanalyzed intimations"""
    reset_connection()
    con = get_connection(":memory:")

    # Insert 2 intimations, one analyzed, one not
    con.raw_sql("""
        INSERT INTO intimations (id, numero_processo, data_disponibilizacao, sigla_tribunal, analyzed, link)
        VALUES (1, '123', '2024-01-01', 'TJRO', FALSE, 'http://pdf1')
    """)
    con.raw_sql("""
        INSERT INTO intimations (id, numero_processo, data_disponibilizacao, sigla_tribunal, analyzed, link)
        VALUES (2, '456', '2024-01-02', 'TJRO', TRUE, 'http://pdf2')
    """)

    res = get_unanalyzed_intimations(con)
    assert len(res) == 1
    assert res[0]["id"] == 1


def test_get_lawyer_stats():
    """Test fetching lawyer stats"""
    reset_connection()
    con = get_connection(":memory:")

    # Insert analyses
    con.raw_sql(
        "INSERT INTO intimations (id, numero_processo, data_disponibilizacao, sigla_tribunal) VALUES (1, '1', '2024-01-01', 'TJRO')"
    )
    con.raw_sql(
        "INSERT INTO intimations (id, numero_processo, data_disponibilizacao, sigla_tribunal) VALUES (2, '2', '2024-01-01', 'TJRO')"
    )

    # Insert wins/losses
    con.raw_sql("""
        INSERT INTO decision_analysis (id, intimation_id, winner_lawyer_oab, winner_lawyer_state, loser_lawyer_oab, loser_lawyer_state, winner_party_name, loser_party_name)
        VALUES (uuid(), 1, '12345', 'RO', '67890', 'RO', 'Winner', 'Loser')
    """)
    con.raw_sql("""
        INSERT INTO decision_analysis (id, intimation_id, winner_lawyer_oab, winner_lawyer_state, loser_lawyer_oab, loser_lawyer_state, winner_party_name, loser_party_name)
        VALUES (uuid(), 2, '67890', 'RO', '12345', 'RO', 'Winner', 'Loser')
    """)

    stats = get_lawyer_stats(con, "12345", "RO")
    assert stats["wins"] == 1
    assert stats["losses"] == 1
    assert stats["total"] == 2
    assert stats["win_rate"] == 0.5
