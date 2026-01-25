"""Tests for the Collection Pipeline."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from causaganha.clients.pje import Intimation
from causaganha.pipeline.collect import collect_metadata_for_all_courts, collect_metadata_for_court


@pytest.fixture
def mock_pje_client() -> AsyncGenerator[AsyncMock, None]:
    """Mock the PJeAPIClient."""
    with patch("causaganha.pipeline.collect.PJeAPIClient") as mock:
        client_instance = AsyncMock()
        mock.return_value = client_instance
        yield client_instance


@pytest.fixture
def mock_storage() -> AsyncGenerator[dict[str, MagicMock], None]:
    """Mock storage functions."""
    with patch("causaganha.pipeline.collect.store_intimations") as mock_store, \
         patch("causaganha.pipeline.collect.store_lawyer_associations") as mock_assoc, \
         patch("causaganha.pipeline.collect.get_connection") as mock_conn:
        yield {
            "store_intimations": mock_store,
            "store_lawyer_associations": mock_assoc,
            "get_connection": mock_conn,
        }


@pytest.mark.asyncio
async def test_collect_metadata_success(
    mock_pje_client: AsyncMock,
    mock_storage: dict[str, MagicMock],
) -> None:
    """Test successful metadata collection."""
    # Setup mock data
    intimation = MagicMock(spec=Intimation)
    intimation.id = 1
    intimation.destinatarioadvogados = []

    mock_pje_client.get_intimations_by_court.return_value = [intimation]

    mock_storage["store_intimations"].return_value = 1
    mock_storage["store_lawyer_associations"].return_value = 0

    # Run function
    days_back = 7
    result = await collect_metadata_for_court("TJRO", days_back=days_back)

    # Verify
    assert result["status"] == "success"
    assert result["intimations_fetched"] == 1
    assert result["intimations_new"] == 1

    mock_pje_client.get_intimations_by_court.assert_called_once()
    mock_storage["store_intimations"].assert_called_once()
    mock_storage["store_lawyer_associations"].assert_called_once()


@pytest.mark.asyncio
async def test_collect_metadata_failure(
    mock_pje_client: AsyncMock,
    mock_storage: dict[str, MagicMock],  # noqa: ARG001
) -> None:
    """Test failure handling."""
    mock_pje_client.get_intimations_by_court.side_effect = Exception("API Error")

    result = await collect_metadata_for_court("TJRO")

    assert result["status"] == "failed"
    assert "API Error" in result["error"]


@pytest.mark.asyncio
async def test_collect_all_courts(
    mock_pje_client: AsyncMock,
    mock_storage: dict[str, MagicMock],  # noqa: ARG001
) -> None:
    """Test collecting for multiple courts."""
    # Mock return values for separate calls (simulated by same mock)
    mock_pje_client.get_intimations_by_court.return_value = []

    courts = ["TJRO", "TJMT"]
    results = await collect_metadata_for_all_courts(courts)

    assert len(results) == len(courts)
    assert mock_pje_client.get_intimations_by_court.call_count == len(courts)
