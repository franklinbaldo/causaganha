from unittest.mock import AsyncMock

import pytest

from causaganha.config import settings
from causaganha.pipeline.collect import run_collection


@pytest.mark.asyncio
async def test_run_collection_iterates_courts() -> None:
    """Test that run_collection iterates over provided courts."""
    # Mocks
    repository = AsyncMock()
    client = AsyncMock()

    # Setup client mock to return some data so it proceeds to store
    client.get_intimations_by_court.return_value = [{"id": 1}]

    courts = ["TJRO", "TJSP"]
    start_date = "2023-01-01"
    end_date = "2023-01-02"

    await run_collection(
        repository=repository,
        client=client,
        start_date=start_date,
        end_date=end_date,
        courts=courts,
    )

    # Verify calls
    assert client.get_intimations_by_court.call_count == 2

    # Check calls arguments
    calls = client.get_intimations_by_court.call_args_list
    # Note: args/kwargs matching
    # call 1
    assert calls[0].kwargs["sigla_tribunal"] == "TJRO"
    # call 2
    assert calls[1].kwargs["sigla_tribunal"] == "TJSP"


@pytest.mark.asyncio
async def test_run_collection_uses_settings_defaults() -> None:
    """Test that run_collection uses settings.COURTS if courts is None."""
    repository = AsyncMock()
    client = AsyncMock()

    # We need to mock settings.COURTS.
    # collect.py does: from causaganha.config import settings
    # We can patch causaganha.config.settings

    with pytest.MonkeyPatch.context() as mp:
        # Create a mock settings object or patch the attribute
        # Since 'settings' is an instance in config.py, we patch the attribute on it
        mp.setattr(settings, "COURTS", ["TJMG"])

        await run_collection(
            repository=repository,
            client=client,
            start_date="2023-01-01",
            end_date="2023-01-02",
            courts=None,
        )

        assert client.get_intimations_by_court.call_count == 1
        assert client.get_intimations_by_court.call_args.kwargs["sigla_tribunal"] == "TJMG"
