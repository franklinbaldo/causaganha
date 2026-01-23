"""End-to-end test for the full V2 lifecycle."""

from unittest.mock import AsyncMock, patch

import pytest
from ibis.backends.duckdb import Backend

from causaganha.analysis.models import DecisionAnalysis
from causaganha.api.client import Intimation, LawyerInfo
from causaganha.pipeline.analyze import analyze_pending_decisions
from causaganha.pipeline.collect import collect_metadata_for_court
from causaganha.pipeline.score import calculate_ratings


@pytest.fixture
def mock_intimations() -> list[Intimation]:
    """Provide mock intimations."""
    return [
        Intimation(
            id=1,
            numero_processo="1234567-89.2024.8.22.0001",
            siglaTribunal="TJRO",
            data_disponibilizacao="2024-01-01",
            link="http://example.com/1.pdf",
            destinatarioadvogados=[
                {
                    "advogado": LawyerInfo(
                        id=1,
                        nome="Advogado A",
                        numero_oab="1234",
                        uf_oab="RO",
                    ),
                },
                {
                    "advogado": LawyerInfo(
                        id=2,
                        nome="Advogado B",
                        numero_oab="5678",
                        uf_oab="RO",
                    ),
                },
            ],
        ),
    ]


@pytest.fixture
def mock_analysis() -> DecisionAnalysis:
    """Provide mock decision analysis."""
    return DecisionAnalysis(
        winner_lawyer_oab="1234",
        winner_lawyer_state="RO",
        winner_party_name="Winner",
        loser_lawyer_oab="5678",
        loser_lawyer_state="RO",
        loser_party_name="Loser",
        decision_type="sentença",
        outcome="procedente",
        judge_name="Judge",
        decision_reasoning="Reasoning",
        confidence_score=0.9,
    )


@pytest.mark.asyncio
async def test_full_lifecycle(
    db_connection: Backend,
    mock_intimations: list[Intimation],
    mock_analysis: DecisionAnalysis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the full lifecycle: Collect -> Analyze -> Score."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    # 1. Collect Metadata
    with patch("causaganha.v2.pipeline.collect.PJeAPIClient") as mock_client:
        client_instance = mock_client.return_value
        client_instance.get_intimations_by_court = AsyncMock(
            return_value=mock_intimations,
        )
        client_instance.close = AsyncMock()

        collect_result = await collect_metadata_for_court("TJRO", days_back=1)
        assert collect_result["status"] == "success"
        assert collect_result["intimations_new"] == 1

        # Check intimation stored
        t_intimations = db_connection.table("intimations")
        assert t_intimations.count().execute() == 1

        # Check lawyers stored
        t_lawyers = db_connection.table("intimation_lawyers")
        assert t_lawyers.count().execute() >= 2

    # 2. Analyze Decisions
    with patch("causaganha.v2.pipeline.analyze.DecisionAnalyzer") as mock_analyzer:
        analyzer_instance = mock_analyzer.return_value
        analyzer_instance.analyze_batch = AsyncMock(return_value=[mock_analysis])

        # Use strategy="llm" to skip RAG init
        analyze_result = await analyze_pending_decisions(batch_size=10, strategy="llm")
        assert analyze_result["status"] == "success"
        assert analyze_result["analyzed"] == 1

        # Check analysis stored
        t_analysis = db_connection.table("decision_analysis")
        assert t_analysis.count().execute() == 1

        # Verify intimation is analyzed
        t_intimations = db_connection.table("intimations")
        res = t_intimations.execute()
        assert res.iloc[0]["analyzed"]

    # 3. Calculate Ratings
    # Ensure update_lawyer_rating is using the correct table
    score_result = await calculate_ratings(batch_size=10)
    assert score_result["status"] == "success"
    assert score_result["processed"] == 1

    # Check ratings updated
    t_ratings = db_connection.table("lawyer_ratings")
    ratings = t_ratings.execute()

    # We expect 2 lawyers to be rated (winner and loser)
    assert len(ratings) == 2

    winner = ratings[ratings["oab_number"] == "1234"].iloc[0]
    loser = ratings[ratings["oab_number"] == "5678"].iloc[0]

    # Winner should have higher mu (default 25.0)
    assert winner["mu"] > 25.0
    assert winner["wins"] == 1

    # Loser should have lower mu
    assert loser["mu"] < 25.0
    assert loser["losses"] == 1
