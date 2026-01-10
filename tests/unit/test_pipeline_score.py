import pytest
from unittest.mock import AsyncMock, patch
from causaganha.pipeline.score import run_scoring
from causaganha.storage.repositories.analysis import AnalysisRepository
from causaganha.storage.repositories.lawyer import LawyerRatingRepository

@pytest.fixture
def mock_analysis_repo():
    return AsyncMock(spec=AnalysisRepository)

@pytest.fixture
def mock_rating_repo():
    return AsyncMock(spec=LawyerRatingRepository)

@pytest.mark.asyncio
async def test_run_scoring(mock_analysis_repo, mock_rating_repo):
    with patch("causaganha.pipeline.score.ScoringService") as MockScoringService:
        mock_service_instance = MockScoringService.return_value
        mock_service_instance.process_pending_batch = AsyncMock(return_value=10)

        await run_scoring(mock_analysis_repo, mock_rating_repo, limit=50)

        MockScoringService.assert_called_once_with(mock_analysis_repo, mock_rating_repo)
        mock_service_instance.process_pending_batch.assert_called_once_with(limit=50)
