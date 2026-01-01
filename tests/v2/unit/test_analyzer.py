"""Unit tests for Pydantic AI Decision Analyzer (v2)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from causaganha.v2.analysis.analyzer import DecisionAnalyzer
from causaganha.v2.analysis.models import DecisionAnalysis


@pytest.fixture
def analyzer():
    # We mock the Agent creation to avoid pydantic-ai trying to validate the provider/model
    with patch("causaganha.v2.analysis.analyzer.Agent") as MockAgent:
        # The analyzer init will call Agent(...)
        # We want to return a mock instance
        mock_agent_instance = MagicMock()
        MockAgent.return_value = mock_agent_instance

        # Initialize analyzer
        analyzer = DecisionAnalyzer(model_name="test-model", provider="google-gla")

        # Replace the agent attribute with our mock (though it should be already if patched correctly)
        analyzer.agent = mock_agent_instance
        return analyzer


@pytest.mark.asyncio
async def test_analyze_pdf_success(analyzer) -> None:
    """Test successful PDF analysis."""
    # Mock result
    mock_result = DecisionAnalysis(
        winner_lawyer_oab="1234",
        winner_lawyer_state="RO",
        winner_party_name="Winner",
        loser_lawyer_oab="5678",
        loser_lawyer_state="RO",
        loser_party_name="Loser",
        decision_type="sentença",
        outcome="procedente",
        judge_name="Judge Dredd",
        decision_reasoning="Because.",
        confidence_score=0.9,
    )

    # Mock the Agent.run method
    mock_run_result = MagicMock()
    mock_run_result.data = mock_result

    # Configure the mock agent's run method
    analyzer.agent.run = AsyncMock(return_value=mock_run_result)

    result = await analyzer.analyze_pdf("http://example.com/doc.pdf")

    assert result == mock_result
    assert result.winner_lawyer_oab == "1234"
    analyzer.agent.run.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_batch_success(analyzer) -> None:
    """Test batch analysis."""
    mock_result = DecisionAnalysis(
        winner_lawyer_oab="1234",
        winner_lawyer_state="RO",
        winner_party_name="Winner",
        loser_lawyer_oab="5678",
        loser_lawyer_state="RO",
        loser_party_name="Loser",
        decision_type="sentença",
        outcome="procedente",
        judge_name="Judge Dredd",
        decision_reasoning="Because.",
        confidence_score=0.9,
    )

    # Mock analyze_pdf method to avoid testing Agent internals again
    with patch.object(analyzer, "analyze_pdf", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = mock_result

        results = await analyzer.analyze_batch(["url1", "url2"])

        assert len(results) == 2
        assert results[0] == mock_result
        assert results[1] == mock_result
        assert mock_analyze.call_count == 2


@pytest.mark.asyncio
async def test_analyze_batch_partial_failure(analyzer) -> None:
    """Test batch analysis with some failures."""
    mock_result = DecisionAnalysis(
        winner_lawyer_oab="1234",
        winner_lawyer_state="RO",
        winner_party_name="Winner",
        loser_lawyer_oab="5678",
        loser_lawyer_state="RO",
        loser_party_name="Loser",
        decision_type="sentença",
        outcome="procedente",
        judge_name="Judge Dredd",
        decision_reasoning="Because.",
        confidence_score=0.9,
    )

    with patch.object(analyzer, "analyze_pdf", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.side_effect = [mock_result, Exception("Failed")]

        results = await analyzer.analyze_batch(["url1", "url2"])

        # Should return only successes
        assert len(results) == 1
        assert results[0] == mock_result
