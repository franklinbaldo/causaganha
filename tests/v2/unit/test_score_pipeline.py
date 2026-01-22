"""Unit tests for the scoring pipeline."""

import pytest
from ibis.backends.duckdb import Backend

from causaganha.v2.analysis.models import DecisionAnalysis
from causaganha.v2.pipeline.score import calculate_ratings
from causaganha.v2.storage.queries import store_analysis


@pytest.fixture
def mock_analysis_data() -> DecisionAnalysis:
    """Provide mock decision analysis."""
    return DecisionAnalysis(
        winner_lawyer_oab="5733",
        winner_lawyer_state="RO",
        winner_party_name="Winner",
        loser_lawyer_oab="1234",
        loser_lawyer_state="RO",
        loser_party_name="Loser",
        decision_type="sentença",
        outcome="procedente",
        judge_name="Judge",
        decision_reasoning="Reasoning",
        confidence_score=0.9,
    )


@pytest.mark.asyncio
async def test_calculate_ratings(
    db_connection: Backend,
    mock_analysis_data: DecisionAnalysis,
) -> None:
    """Test rating calculation."""
    # 1. Setup: Insert an analysis record
    # We need an intimation first because of FK
    db_connection.con.execute(
        "INSERT INTO intimations (id, numero_processo, data_disponibilizacao, sigla_tribunal, analyzed) VALUES (1, '123', '2024-01-01', 'TJRO', TRUE)",
    )
    store_analysis(db_connection, 1, mock_analysis_data)

    # 2. Run scoring
    result = await calculate_ratings()

    assert result["status"] == "success"
    assert result["processed"] > 0

    # 3. Verify ratings updated
    ratings = db_connection.table("lawyer_ratings").execute()
    assert len(ratings) >= 2  # Winner and loser

    winner_rating = ratings[ratings["oab_number"] == "5733"].iloc[0]
    loser_rating = ratings[ratings["oab_number"] == "1234"].iloc[0]

    assert winner_rating["wins"] == 1
    assert loser_rating["losses"] == 1
    assert winner_rating["mu"] > 25.0  # Winner rating increased
    assert loser_rating["mu"] < 25.0  # Loser rating decreased
