import ibis
import pytest

from causaganha.v2.api.models import Intimation
from causaganha.v2.storage.connection import get_connection, reset_connection
from causaganha.v2.storage.queries import store_intimations


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
