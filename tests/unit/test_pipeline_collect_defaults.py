from unittest.mock import AsyncMock, patch

import pytest

from causaganha.pipeline.collect import run_collection


@pytest.mark.asyncio
async def test_run_collection_default_courts() -> None:
    """Test that run_collection uses configured courts if none provided."""
    mock_repo = AsyncMock()
    mock_client = AsyncMock()

    # Mock the Settings instance, not the class
    with patch("causaganha.config.settings.COURTS", ["TJAC", "TJRR"]):
        await run_collection(
            repository=mock_repo,
            client=mock_client,
            start_date="2024-01-01",
            end_date="2024-01-01",
            courts=None,
        )

    # Verify API was called twice (once for each court)
    assert mock_client.get_intimations_by_court.call_count == 2

    calls = mock_client.get_intimations_by_court.call_args_list
    courts_called = [c.kwargs["sigla_tribunal"] for c in calls]
    assert "TJAC" in courts_called
    assert "TJRR" in courts_called
