import pytest
import pytest_asyncio

from causaganha_v2.api.client import PJeAPIClient


@pytest_asyncio.fixture
async def api_client():
    """Provide a clean API client for tests"""
    client = PJeAPIClient()
    yield client
    await client.close()
