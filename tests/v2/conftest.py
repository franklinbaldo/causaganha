import pytest
import pytest_asyncio

from causaganha.v2.api.client import PJeAPIClient
from causaganha.v2.storage.connection import get_connection


@pytest.fixture
def db_connection():
    """Provide an in-memory database for tests"""
    from causaganha.v2.storage import connection

    # Force new connection for each test
    connection._connection = None

    con = get_connection(":memory:")
    yield con

    # Cleanup
    connection._connection = None


@pytest_asyncio.fixture
async def api_client():
    """Provide a clean API client for tests"""
    client = PJeAPIClient()
    yield client
    await client.close()
