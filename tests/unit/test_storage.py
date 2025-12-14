from pathlib import Path
from datetime import date

import pytest
from ibis import BaseBackend

from causaganha.domain.models import Intimation
from causaganha.storage.connection import get_connection
from causaganha.storage.queries import store_intimations
from causaganha.storage.schema import create_schema


@pytest.fixture
def mem_conn() -> BaseBackend:
    con = get_connection(":memory:")
    create_schema(con)
    return con


def test_schema_initialization(mem_conn: BaseBackend) -> None:
    tables = mem_conn.list_tables()
    assert "intimations" in tables
    assert "pipeline_state" in tables


@pytest.mark.asyncio
async def test_store_intimations(mem_conn: BaseBackend) -> None:
    # Create a sample intimation
    intimation = Intimation(
        id=12345,
        numero_processo="1234567-89.2024.8.00.0000",
        data_disponibilizacao=date(2024, 5, 23),
        sigla_tribunal="TJSP",
        tipo_comunicacao="Intimação",
        nome_orgao="Vara Cível",
        texto="Texto da intimação",
        link="http://example.com",
        tipo_documento="Despacho",
        nome_classe="Procedimento Comum",
        hash="abc123hash",
        status="PENDING",
    )

    await store_intimations(mem_conn, [intimation])

    t = mem_conn.table("intimations")
    result = t.execute()

    assert len(result) == 1
    assert result.iloc[0]["id"] == 12345
    assert result.iloc[0]["sigla_tribunal"] == "TJSP"


@pytest.mark.asyncio
async def test_store_intimations_empty(mem_conn: BaseBackend) -> None:
    await store_intimations(mem_conn, [])
    t = mem_conn.table("intimations")
    result = t.execute()
    assert len(result) == 0


def test_get_connection_file(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    con = get_connection(str(db_path))
    assert con is not None
