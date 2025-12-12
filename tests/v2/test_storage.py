import pytest
from causaganha.v2.storage.connection import get_connection
from causaganha.v2.storage.queries import store_intimations, store_lawyer_associations, get_unanalyzed_intimations
from causaganha.v2.api.models import Intimation, LawyerInfo, DestinatarioAdvogado

def test_connection_initializes_schema(db_connection):
    """Test that connection creates tables"""
    assert db_connection is not None
    tables = db_connection.list_tables()
    assert "intimations" in tables
    assert "intimation_lawyers" in tables
    assert "decision_analysis" in tables

def test_store_intimations(db_connection):
    """Test storing intimations"""
    data = {
        "id": 123456,
        "numero_processo": "0001234-56.2024.8.22.0001",
        "data_disponibilizacao": "2024-12-01",
        "siglaTribunal": "TJRO",
        "tipoComunicacao": "INTIMACAO",
        "nomeOrgao": "Vara Civel",
        "texto": "Decisao...",
        "link": "https://pje.tjro.jus.br/doc/12345.pdf",
        "tipoDocumento": "Despacho",
        "nomeClasse": "Procedimento Comum",
        "hash": "abc123hash",
        "status": "A",
        "destinatarioadvogados": [],
    }
    intimation = Intimation(**data)

    count = store_intimations(db_connection, [intimation])
    assert count == 1

    # Verify it's in DB
    t = db_connection.table("intimations")
    assert t.count().execute() == 1

    # Verify fields
    res = t.execute()
    assert res["id"][0] == 123456
    assert res["sigla_tribunal"][0] == "TJRO"

def test_store_lawyer_associations(db_connection):
    """Test storing lawyer associations"""
    # Create intimation first (FK constraint)
    data = {
        "id": 123456,
        "numero_processo": "0001234-56.2024.8.22.0001",
        "data_disponibilizacao": "2024-12-01",
        "siglaTribunal": "TJRO",
        "tipoComunicacao": "INTIMACAO",
        "nomeOrgao": "Vara Civel",
        "texto": "Decisao...",
        "link": "https://pje.tjro.jus.br/doc/12345.pdf",
        "tipoDocumento": "Despacho",
        "nomeClasse": "Procedimento Comum",
        "hash": "abc123hash",
        "status": "A",
        "destinatarioadvogados": [],
    }
    intimation = Intimation(**data)
    store_intimations(db_connection, [intimation])

    # Lawyer data
    lawyers = [
        DestinatarioAdvogado(
            advogado=LawyerInfo(
                id=1,
                nome="FRANKLIN SILVEIRA BALDO",
                numero_oab="5733",
                uf_oab="RO"
            )
        )
    ]

    count = store_lawyer_associations(db_connection, 123456, lawyers)
    assert count == 1

    t = db_connection.table("intimation_lawyers")
    assert t.count().execute() == 1
    res = t.execute()
    assert res["lawyer_name"][0] == "FRANKLIN SILVEIRA BALDO"

def test_get_unanalyzed_intimations(db_connection):
    """Test retrieving unanalyzed intimations"""
    # 1. Store one unanalyzed
    data1 = {
        "id": 1,
        "numero_processo": "proc1",
        "data_disponibilizacao": "2024-12-01",
        "siglaTribunal": "TJRO",
        "tipoComunicacao": "INTIMACAO",
        "nomeOrgao": "Vara Civel",
        "texto": "Decisao...",
        "link": "https://example.com/1.pdf", # Has link
        "tipoDocumento": "Despacho",
        "nomeClasse": "Procedimento Comum",
        "hash": "hash1",
        "status": "A",
    }
    store_intimations(db_connection, [Intimation(**data1)])

    # 2. Store one already analyzed (manually update or store via similar method)
    # Since store_intimations defaults analyzed=False, we need to update it
    # But we can't update yet as we don't have update function exposed in queries (only manually via sql)

    # Or we can just test that the one we inserted is returned.

    pending = get_unanalyzed_intimations(db_connection)
    assert len(pending) == 1
    assert pending[0]['id'] == 1

    # Manually mark as analyzed using raw SQL
    db_connection.raw_sql("UPDATE intimations SET analyzed = TRUE WHERE id = 1")

    pending = get_unanalyzed_intimations(db_connection)
    assert len(pending) == 0
