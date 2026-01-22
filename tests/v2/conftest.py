"""Shared test fixtures following TDD principles.

Fixtures are written as tests are written.
"""

from collections.abc import AsyncGenerator, Generator

import pytest
from ibis.backends.duckdb import Backend

from causaganha.api.client import PJeAPIClient
from causaganha.storage.connection import get_connection


@pytest.fixture
async def api_client() -> AsyncGenerator[PJeAPIClient, None]:
    """Provide a clean API client for tests."""
    client = PJeAPIClient()
    yield client
    await client.close()


@pytest.fixture
def db_connection() -> Generator[Backend, None, None]:
    """Provide an in-memory database for tests."""
    import causaganha.storage.connection

    # Reset singleton
    causaganha.v2.storage.connection._connection = None

    con = get_connection(":memory:")
    yield con

    # Cleanup
    con.disconnect()
    causaganha.v2.storage.connection._connection = None
