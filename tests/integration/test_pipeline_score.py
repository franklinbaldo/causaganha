"""Integration tests for scoring pipeline."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from causaganha.pipeline.score import run_scoring
from causaganha.scoring.openskill import Rating, create_rating, get_openskill_model
from causaganha.storage.repositories.lawyer import LawyerRatingRepository


@pytest.fixture
def mock_repository():
    return AsyncMock()

@pytest.fixture
def mock_lawyer_repository():
    return AsyncMock(spec=LawyerRatingRepository)

@pytest.mark.asyncio
async def test_run_scoring(mock_repository, mock_lawyer_repository):
    """Test full scoring pipeline logic."""

    # 1. Setup mock data
    unscored_analysis = [
        {
            "id": 1,
            "intimation_id": 101,
            "winner_lawyer_oab": "123",
            "winner_lawyer_state": "RO",
            "loser_lawyer_oab": "456",
            "loser_lawyer_state": "RO",
        },
    ]
    mock_repository.get_unscored_analyses.return_value = unscored_analysis

    # 2. Setup existing ratings (one exists, one new)
    existing_ratings = [
        {
            "oab_number": "123",
            "oab_state": "RO",
            "mu": 28.0,
            "sigma": 8.0,
            "total_cases": 5,
            "wins": 3,
            "losses": 2,
        },
    ]
    mock_lawyer_repository.get_lawyer_ratings.return_value = existing_ratings

    # 3. Run pipeline
    await run_scoring(mock_repository, mock_lawyer_repository, limit=10)

    # 4. Verify interactions

    # Should fetch unscored
    mock_repository.get_unscored_analyses.assert_called_once_with(limit=10)

    # Should fetch existing ratings for both lawyers
    # Order of OABs in call is set-dependent, so we check contents
    call_args = mock_lawyer_repository.get_lawyer_ratings.call_args[0][0]
    assert ("123", "RO") in call_args
    assert ("456", "RO") in call_args

    # Should save updated ratings
    mock_lawyer_repository.save_lawyer_ratings.assert_called_once()
    saved_ratings = mock_lawyer_repository.save_lawyer_ratings.call_args[0][0]
    assert len(saved_ratings) == 2

    # Winner (123) should increase mu
    winner = next(r for r in saved_ratings if r["oab_number"] == "123")
    assert winner["mu"] > 28.0
    assert winner["total_cases"] == 6
    assert winner["wins"] == 4

    # Loser (456) was new (default mu=25), should decrease
    loser = next(r for r in saved_ratings if r["oab_number"] == "456")
    assert loser["mu"] < 25.0
    assert loser["total_cases"] == 1
    assert loser["losses"] == 1

    # Should mark analysis as scored
    mock_repository.mark_analyses_scored.assert_called_once_with([1])
