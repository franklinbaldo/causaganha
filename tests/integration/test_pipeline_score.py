from datetime import UTC, datetime
from pathlib import Path

import pytest

from causaganha.pipeline.score import run_scoring
from causaganha.storage.connection import get_connection
from causaganha.storage.repositories.analysis import AnalysisRepository
from causaganha.storage.repositories.intimation import IntimationRepository
from causaganha.storage.repositories.lawyer import LawyerRatingRepository
from causaganha.storage.schema import create_schema


@pytest.mark.asyncio
async def test_run_scoring(tmp_path: Path) -> None:
    db_path = tmp_path / "test_scoring.duckdb"
    con = get_connection(str(db_path))
    create_schema(con)

    # Insert fake analysis result
    analysis_repo = AnalysisRepository(con)

    analysis_data = {
        "id": 1,
        "intimation_id": 101,
        "outcome": "WIN",
        "summary": "Summary",
        "judge_name": "Judge",
        "confidence_score": 0.9,
        "analyzed_at": datetime.now(UTC),
        "winner_lawyer_oab": "123",
        "winner_lawyer_state": "RO",
        "winner_party_name": "Winner",
        "loser_lawyer_oab": "456",
        "loser_lawyer_state": "RO",
        "loser_party_name": "Loser",
        "decision_type": "SENTENCE",
        "decision_reasoning": "Reason",
    }

    await analysis_repo.store_analysis_results_batch([analysis_data])

    # Run scoring
    rating_repo = LawyerRatingRepository(con)
    await run_scoring(analysis_repo, rating_repo)

    # Verify lawyer ratings
    t = con.table("lawyer_ratings")
    ratings = t.execute()

    assert len(ratings) == 2

    winner = ratings[ratings["oab_number"] == "123"].iloc[0]
    loser = ratings[ratings["oab_number"] == "456"].iloc[0]

    # Default mu is 25.0
    assert winner["mu"] > 25.0
    assert loser["mu"] < 25.0
    assert winner["wins"] == 1
    assert loser["losses"] == 1
    assert winner["total_cases"] == 1
