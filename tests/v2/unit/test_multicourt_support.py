import os
from unittest import mock

import pytest

from causaganha.api.client import PJeAPIClient
from causaganha.config import Settings
from causaganha.pipeline.collect import run_collection
from causaganha.storage.repository import IntimationRepository


def test_settings_courts_parsing() -> None:
    """Test that COURTS can be parsed from JSON string in env var."""
    with mock.patch.dict(os.environ, {"COURTS": '["TJRO", "TJMT", "TJSP"]'}):
        # We must instantiate Settings directly to trigger parsing
        settings = Settings()
        assert settings.COURTS == ["TJRO", "TJMT", "TJSP"]

    # Verify default
    with mock.patch.dict(os.environ, {}, clear=True):
        # We might need to ensure COURTS is not in env
        if "COURTS" in os.environ:
             del os.environ["COURTS"]
        settings = Settings()
        assert settings.COURTS == ["TJRO"]

@pytest.mark.asyncio
async def test_run_collection_multicourt() -> None:
    """Test that run_collection iterates over multiple courts."""
    # Mock dependencies
    mock_repo = mock.AsyncMock(spec=IntimationRepository)
    mock_client = mock.AsyncMock(spec=PJeAPIClient)

    # Setup mock return to avoid iteration error if it expects something
    mock_client.get_intimations_by_court.return_value = []

    courts = ["TJRO", "TJMT"]

    await run_collection(
        repository=mock_repo,
        client=mock_client,
        start_date="2023-01-01",
        end_date="2023-01-02",
        courts=courts,
    )

    # Verify calls
    assert mock_client.get_intimations_by_court.call_count == 2

    # Check calls
    calls = mock_client.get_intimations_by_court.call_args_list
    # calls[0] is (args, kwargs)
    assert calls[0].kwargs["sigla_tribunal"] == "TJRO"
    assert calls[1].kwargs["sigla_tribunal"] == "TJMT"

@pytest.mark.asyncio
async def test_run_collection_failure_resilience() -> None:
    """Test that run_collection continues if one court fails."""
    mock_repo = mock.AsyncMock(spec=IntimationRepository)
    mock_client = mock.AsyncMock(spec=PJeAPIClient)

    # First call raises, second succeeds
    mock_client.get_intimations_by_court.side_effect = [
        Exception("TJRO Network Error"),
        [],
    ]

    courts = ["TJRO", "TJMT"]

    # Should not raise
    await run_collection(
        repository=mock_repo,
        client=mock_client,
        start_date="2023-01-01",
        end_date="2023-01-02",
        courts=courts,
    )

    assert mock_client.get_intimations_by_court.call_count == 2
