import asyncio

import pytest
from ibis import BaseBackend

from causaganha.api.models import Intimation
from causaganha.v2.storage.connection import get_connection
from causaganha.v2.storage.queries import store_intimations
from causaganha.v2.storage.schema import create_schema


@pytest.fixture
async def con() -> BaseBackend:
    """Fixture for in-memory database connection."""
    conn = await get_connection(":memory:")
    await create_schema(conn)
    return conn


@pytest.mark.asyncio
async def test_schema_creation(con: BaseBackend) -> None:
    tables = await asyncio.to_thread(con.list_tables)
    assert "intimations" in tables

    t = con.table("intimations")
    schema = t.schema()
    assert "sigla_tribunal" in schema.names
    assert "data_disponibilizacao" in schema.names


@pytest.mark.asyncio
async def test_store_intimations(con: BaseBackend) -> None:
    intimation = Intimation(
        id=123,
        numero_processo="123456",
        data_disponibilizacao="2024-01-01",
        siglaTribunal="TJSP",
        tipoComunicacao="Intimacao",
        nomeOrgao="Vara 1",
        texto="Texto da intimação",
        link="http://link.com",
        tipoDocumento="Despacho",
        nomeClasse="Procedimento Comum",
        hash="abc",
        status="A",
    )

    # Store
    await store_intimations(con, [intimation])

    # Verify
    t = con.table("intimations")
    result = await asyncio.to_thread(t.execute)

    assert len(result) == 1
    row = result.iloc[0]
    assert row["id"] == 123
    assert row["sigla_tribunal"] == "TJSP"
    assert row["numero_processo"] == "123456"
