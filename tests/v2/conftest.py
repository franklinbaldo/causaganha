"""Shared test fixtures following TDD principles.

Fixtures are written as tests are written.
"""

from collections.abc import AsyncGenerator

import pytest

from causaganha.v2.api.client import PJeAPIClient


@pytest.fixture
async def api_client() -> AsyncGenerator[PJeAPIClient, None]:
    """Provide a clean API client for tests."""
    client = PJeAPIClient()
    yield client
    await client.close()
