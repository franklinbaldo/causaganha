"""Integration tests for the pipeline."""

from unittest.mock import AsyncMock, patch

import pytest
from ibis.backends.duckdb import Backend

from causaganha.v2.analysis.models import DecisionAnalysis
from causaganha.v2.api.client import Intimation
from causaganha.v2.pipeline.analyze import analyze_pending_decisions
from causaganha.v2.pipeline.collect import collect_metadata_for_court


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
        ),
    ]


@pytest.fixture
def mock_analysis() -> DecisionAnalysis:
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
async def test_full_pipeline_mocked(
    db_connection: Backend,
    mock_intimations: list[Intimation],
    mock_analysis: DecisionAnalysis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the full pipeline with mocked external services."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    # 1. Mock API Client for Collection
    with patch("causaganha.v2.pipeline.collect.PJeAPIClient") as mock_client:
        client_instance = mock_client.return_value
        client_instance.get_intimations_by_court = AsyncMock(
            return_value=mock_intimations,
        )
        client_instance.close = AsyncMock()

        # Run collection
        collect_result = await collect_metadata_for_court("TJRO", days_back=1)

        assert collect_result["status"] == "success"
        assert collect_result["intimations_new"] == 1

        # Verify DB has intimation
        t = db_connection.table("intimations")
        result = t.execute()
        assert len(result) == 1
        assert result.iloc[0]["id"] == 1
        assert not result.iloc[0]["analyzed"]

    # 2. Mock Analyzer for Analysis
    with patch("causaganha.v2.pipeline.analyze.DecisionAnalyzer") as mock_analyzer:
        analyzer_instance = mock_analyzer.return_value
        analyzer_instance.analyze_batch = AsyncMock(return_value=[mock_analysis])

        # Run analysis
        analyze_result = await analyze_pending_decisions(batch_size=10)

        assert analyze_result["status"] == "success"
        assert analyze_result["analyzed"] == 1

        # Verify DB has analysis and intimation is marked analyzed
        t = db_connection.table("decision_analysis")
        result = t.execute()
        assert len(result) == 1
        assert result.iloc[0]["winner_lawyer_oab"] == "5733"

        t_intimations = db_connection.table("intimations")
        res_intimations = t_intimations.execute()
        assert res_intimations.iloc[0]["analyzed"]
