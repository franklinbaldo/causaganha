import pytest
from unittest.mock import AsyncMock, patch
from causaganha.pipeline.collect import run_collection

@pytest.mark.asyncio
async def test_run_collection_uses_configured_courts() -> None:
    """Test that run_collection uses settings.COURTS when courts argument is None."""
    mock_repo = AsyncMock()
    mock_client = AsyncMock()

    # Configure mocks
    mock_client.get_intimations_by_court.return_value = []

    test_courts = ["TJMT", "TJSP"]

    with patch("causaganha.pipeline.collect.settings") as mock_settings:
        mock_settings.COURTS = test_courts

        await run_collection(
            repository=mock_repo,
            client=mock_client,
            start_date="2024-01-01",
            end_date="2024-01-01",
            courts=None
        )

        # Verify call count matches number of configured courts
        assert mock_client.get_intimations_by_court.call_count == 2

        # Verify correct tribunals were passed
        calls = mock_client.get_intimations_by_court.call_args_list
        tribunals = sorted([c.kwargs["sigla_tribunal"] for c in calls])
        assert tribunals == ["TJMT", "TJSP"]
