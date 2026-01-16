"""Unit tests for the storage layer."""

from pathlib import Path

import ibis
from ibis.backends.duckdb import Backend

from causaganha.v2.api.client import Intimation
from causaganha.v2.storage.connection import get_connection
from causaganha.v2.storage.queries import store_intimations


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
