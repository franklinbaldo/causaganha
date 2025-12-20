from pathlib import Path
from datetime import datetime, timezone
import pytest
import ibis

from causaganha.pipeline.score import run_scoring
from causaganha.storage.connection import get_connection
from causaganha.storage.schema import create_schema
from causaganha.storage.repository import IntimationRepository

@pytest.mark.asyncio
async def test_run_scoring(tmp_path: Path) -> None:
    db_path = tmp_path / "test_scoring.duckdb"
    con = get_connection(str(db_path))
    create_schema(con)

    # Insert fake analysis result
    # We need to use raw SQL or Ibis memtable to insert because there is no helper for just inserting analysis results
    # except store_analysis_result which is async and internal to analyze.py (well, exposed in queries.py)

    from causaganha.storage.queries import store_analysis_result

    analysis_data = {
        "id": 1,
        "intimation_id": 101,
        "outcome": "WIN",
        "summary": "Summary",
        "judge_name": "Judge",
        "confidence_score": 0.9,
        "analyzed_at": datetime.now(timezone.utc),
        "winner_lawyer_oab": "123",
        "winner_lawyer_state": "RO",
        "winner_party_name": "Winner",
        "loser_lawyer_oab": "456",
        "loser_lawyer_state": "RO",
        "loser_party_name": "Loser",
        "decision_type": "SENTENCE",
        "decision_reasoning": "Reason",
    }

    await store_analysis_result(con, analysis_data)

    # Run scoring
    repository = IntimationRepository(con)
    await run_scoring(repository)

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
