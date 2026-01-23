"""Unit tests for the decision analyzer."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from causaganha.analysis.analyzer import DecisionAnalyzer
from causaganha.analysis.models import DecisionAnalysis


@pytest.fixture
def analyzer(monkeypatch: pytest.MonkeyPatch) -> DecisionAnalyzer:
    """Provide a decision analyzer for tests."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    return DecisionAnalyzer(model_name="gemini-2.5-flash")


@pytest.mark.asyncio
async def test_analyze_pdf_success(analyzer: DecisionAnalyzer) -> None:
    """Test successful PDF analysis."""
    # Mock result
    mock_result = DecisionAnalysis(
        winner_lawyer_oab="5733",
        winner_lawyer_state="RO",
        winner_party_name="João da Silva",
        loser_lawyer_oab="6789",
        loser_lawyer_state="RO",
        loser_party_name="Maria Souza",
        decision_type="sentença",
        outcome="procedente",
        judge_name="Dr. José Santos",
        decision_reasoning="Pedido procedente.",
        confidence_score=0.95,
    )

    # Mock agent.run
    mock_run = AsyncMock()
    mock_run.return_value.data = mock_result

    with patch.object(analyzer.agent, "run", new=mock_run):
        result = await analyzer.analyze_pdf("http://example.com/test.pdf")

        assert isinstance(result, DecisionAnalysis)
        assert result.winner_lawyer_oab == "5733"
        assert result.confidence_score == 0.95


@pytest.mark.asyncio
async def test_analyze_batch_success(analyzer: DecisionAnalyzer) -> None:
    """Test batch analysis."""
    mock_result = DecisionAnalysis(
        winner_lawyer_oab="5733",
        winner_lawyer_state="RO",
        winner_party_name="João da Silva",
        loser_lawyer_oab="6789",
        loser_lawyer_state="RO",
        loser_party_name="Maria Souza",
        decision_type="sentença",
        outcome="procedente",
        judge_name="Dr. José Santos",
        decision_reasoning="Pedido procedente.",
        confidence_score=0.95,
    )

    mock_run = AsyncMock()
    mock_run.return_value.data = mock_result

    with patch.object(analyzer.agent, "run", new=mock_run):
        results = await analyzer.analyze_batch(
            ["http://example.com/1.pdf", "http://example.com/2.pdf"],
        )

        assert len(results) == 2
        assert all(isinstance(r, DecisionAnalysis) for r in results)


@pytest.mark.asyncio
async def test_analyze_batch_returns_exceptions(analyzer: DecisionAnalyzer) -> None:
    """Test batch analysis returns exceptions in place."""
    mock_result = DecisionAnalysis(
        winner_lawyer_oab="5733",
        winner_lawyer_state="RO",
        winner_party_name="João da Silva",
        loser_lawyer_oab="6789",
        loser_lawyer_state="RO",
        loser_party_name="Maria Souza",
        decision_type="sentença",
        outcome="procedente",
        judge_name="Dr. José Santos",
        decision_reasoning="Pedido procedente.",
        confidence_score=0.95,
    )

    async def side_effect(*args: object, **_kwargs: object) -> Mock:
        url = args[0]
        if "1.pdf" in str(url):
            return Mock(data=mock_result)
        msg = "Analysis failed"
        raise ValueError(msg)

    with patch.object(analyzer.agent, "run", side_effect=side_effect):
        results = await analyzer.analyze_batch(
            ["http://example.com/1.pdf", "http://example.com/2.pdf"],
        )

        assert len(results) == 2
        assert isinstance(results[0], DecisionAnalysis)
        assert isinstance(results[1], Exception)
