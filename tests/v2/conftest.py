"""Shared test fixtures."""

import pytest

from causaganha.v2.api.client import PJeAPIClient


@pytest.fixture
async def api_client():
    """Provide a clean API client for tests."""
    client = PJeAPIClient()
    yield client
    await client.close()
