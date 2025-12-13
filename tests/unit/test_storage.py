import pytest
from ibis import BaseBackend

from causaganha.api.models import DestinatarioAdvogado, Intimation, LawyerInfo
from causaganha.storage.connection import get_connection
from causaganha.storage.queries import (
    get_unanalyzed_intimations,
    store_intimations,
    store_lawyer_associations,
)


@pytest.fixture
def con() -> BaseBackend:
    # Use in-memory DB for tests
    return get_connection(":memory:")


def test_schema_creation(con: BaseBackend) -> None:
    """Test that schema tables are created automatically."""
    tables = con.list_tables()
    assert "intimations" in tables
    assert "intimation_lawyers" in tables
    assert "decision_analysis" in tables
    assert "pipeline_state" in tables


def test_store_intimations(con: BaseBackend) -> None:
    """Test storing intimations."""
    intimation = Intimation(
        id=123,
        numero_processo="12345",
        data_disponibilizacao="2024-01-01",
        siglaTribunal="TJRO",
        tipoComunicacao="Intimacao",
        nomeOrgao="Vara 1",
        texto="Texto",
        link="http://pdf",
        tipoDocumento="Sentenca",
        nomeClasse="Civil",
        hash="abc",
        status="A",
    )

    # Store
    count = store_intimations(con, [intimation])
    assert count == 1

    # Verify
    t = con.table("intimations")
    rows = t.filter(t.id == 123).execute()
    assert len(rows) == 1
    assert rows.iloc[0]["sigla_tribunal"] == "TJRO"
    assert not rows.iloc[0]["analyzed"]


def test_store_lawyer_associations(con: BaseBackend) -> None:
    """Test storing lawyer associations."""
    # First create intimation (FK constraint might apply if enforced)
    # The schema plan has REFERENCES. DuckDB enforces FKs if tables exist.

    # We need an intimation first
    intimation = Intimation(
        id=456,
        numero_processo="67890",
        data_disponibilizacao="2024-01-01",
        siglaTribunal="TJRO",
        tipoComunicacao="Intimacao",
        nomeOrgao="Vara 1",
        texto="Texto",
        link="http://pdf",
        tipoDocumento="Sentenca",
        nomeClasse="Civil",
        hash="def",
        status="A",
    )
    store_intimations(con, [intimation])

    # Create lawyer data matching API model structure
    lawyer_info = LawyerInfo(
        id=1, nome="Advogado Teste", numero_oab="12345", uf_oab="RO"
    )
    dest_adv = DestinatarioAdvogado(advogado=lawyer_info)

    count = store_lawyer_associations(con, 456, [dest_adv])
    assert count == 1

    # Verify
    t = con.table("intimation_lawyers")
    rows = t.filter(t.intimation_id == 456).execute()
    assert len(rows) == 1
    assert rows.iloc[0]["lawyer_name"] == "Advogado Teste"
    assert rows.iloc[0]["oab_number"] == "12345"


def test_get_unanalyzed_intimations(con: BaseBackend) -> None:
    """Test retrieving unanalyzed intimations."""
    # Store two intimations
    i1 = Intimation(
        id=789,
        numero_processo="111",
        data_disponibilizacao="2024-01-01",
        siglaTribunal="TJRO",
        tipoComunicacao="Intimacao",
        nomeOrgao="Vara 1",
        texto="Texto",
        link="http://pdf1",
        tipoDocumento="Sentenca",
        nomeClasse="Civil",
        hash="g1",
        status="A",
    )
    i2 = Intimation(
        id=790,
        numero_processo="222",
        data_disponibilizacao="2024-01-02",
        siglaTribunal="TJRO",
        tipoComunicacao="Intimacao",
        nomeOrgao="Vara 1",
        texto="Texto",
        link="http://pdf2",
        tipoDocumento="Sentenca",
        nomeClasse="Civil",
        hash="g2",
        status="A",
    )
    store_intimations(con, [i1, i2])

    # Retrieve
    pending = get_unanalyzed_intimations(con)
    assert len(pending) == 2

    # Mark one as analyzed (simulating update)
    con.raw_sql("UPDATE intimations SET analyzed = TRUE WHERE id = 789")

    pending = get_unanalyzed_intimations(con)
    assert len(pending) == 1
    assert pending[0]["id"] == 790
