"""Unit tests for Ibis queries (v2)."""

from unittest.mock import MagicMock

import pytest

from causaganha.v2.storage.connection import get_connection
from causaganha.v2.storage.queries import get_unanalyzed_intimations, store_intimations


@pytest.fixture
def db_connection(tmp_path):
    """Provide a fresh DB connection for each test."""
    db_path = tmp_path / "test.duckdb"
    # We need to reset the singleton for isolation
    with pytest.MonkeyPatch.context() as m:
        m.setattr("causaganha.v2.storage.connection._connection", None)
        return get_connection(str(db_path))


def test_store_intimations(db_connection) -> None:
    """Test storing intimations."""
    # Mock intimation object
    intimation = MagicMock()
    intimation.id = 1
    intimation.numero_processo = "12345"
    intimation.numeroprocessocommascara = "12345-00.2024.8.22.0001"
    intimation.data_disponibilizacao = "2024-01-01"
    intimation.siglaTribunal = "TJRO"
    intimation.idOrgao = 10
    intimation.tipoComunicacao = "Intimação"
    intimation.nomeOrgao = "Vara X"
    intimation.texto = "Texto"
    intimation.link = "http://pdf"
    intimation.tipoDocumento = "Decisão"
    intimation.nomeClasse = "Classe X"
    intimation.codigoClasse = "7"
    intimation.hash = "hash1"
    intimation.status = "D"

    count = store_intimations(db_connection, [intimation])
    assert count == 1

    # Verify insertion
    t = db_connection.table("intimations")
    assert t.count().execute() == 1

    row = t.execute().iloc[0]
    assert row["id"] == 1
    assert row["numero_processo"] == "12345"
    assert not row["analyzed"]


def test_get_unanalyzed_intimations(db_connection) -> None:
    """Test fetching unanalyzed intimations."""
    # Insert test data
    db_connection.raw_sql("""
        INSERT INTO intimations (
            id, numero_processo, data_disponibilizacao, sigla_tribunal,
            link, analyzed, created_at
        ) VALUES
        (1, 'proc1', '2024-01-01', 'TJRO', 'http://pdf1', FALSE, NOW()),
        (2, 'proc2', '2024-01-02', 'TJRO', 'http://pdf2', TRUE, NOW()),
        (3, 'proc3', '2024-01-03', 'TJRO', NULL, FALSE, NOW())
    """)

    results = get_unanalyzed_intimations(db_connection)

    # Should only get ID 1 (analyzed=False AND link not null)
    assert len(results) == 1
    assert results[0]["id"] == 1
    assert results[0]["link"] == "http://pdf1"
