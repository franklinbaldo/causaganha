"""Integration tests for scoring pipeline."""

import pytest
from pathlib import Path
from datetime import datetime, UTC

from causaganha.pipeline.score import run_scoring
from causaganha.storage.connection import get_connection
from causaganha.storage.repository import IntimationRepository
from causaganha.storage.schema import create_schema
from causaganha.domain.models import Intimation

@pytest.mark.asyncio
async def test_run_scoring(tmp_path: Path) -> None:
    db_path = tmp_path / "test_scoring.duckdb"
    con = get_connection(str(db_path))
    create_schema(con)
    repository = IntimationRepository(con)

    # Insert fake analysis result using repository
    analysis_result = {
        "id": 100,
        "intimation_id": 1,
        "outcome": "WIN",
        "summary": "Summary",
        "judge_name": "Judge",
        "confidence_score": 0.9,
        "analyzed_at": datetime.now(UTC),
        "winner_lawyer_oab": "123",
        "winner_lawyer_state": "SP",
        "winner_party_name": "Winner",
        "loser_lawyer_oab": "456",
        "loser_lawyer_state": "SP",
        "loser_party_name": "Loser",
        "decision_type": "Decisao",
        "decision_reasoning": "Reasoning",
        "scored": False
    }

    await repository.store_analysis_result(analysis_result)

    # Run scoring
    await run_scoring(repository, limit=10)

    # Verify scores updated
    # Check if analysis marked as scored
    t = con.table("analysis_results")
    rows = t.filter(t.id == 100).execute().to_dict(orient="records")
    assert rows[0]["scored"] is True

    # Check if ratings created
    t_ratings = con.table("lawyer_ratings")
    ratings = t_ratings.execute().to_dict(orient="records")
    assert len(ratings) == 2

    # Check winners/losers
    winner = [r for r in ratings if r["oab_number"] == "123"][0]
    loser = [r for r in ratings if r["oab_number"] == "456"][0]

    assert winner["wins"] == 1
    assert loser["losses"] == 1
    assert winner["mu"] > loser["mu"]
