"""Unit tests for Decision Analyzer."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from causaganha.domain.models_analysis import BatchDecisionAnalysis, DecisionAnalysis, Outcome
from causaganha.infrastructure.ai.analyzer import DecisionAnalyzer


@pytest.fixture
def mock_agent() -> Generator[MagicMock, None, None]:
    with patch("causaganha.infrastructure.ai.analyzer.Agent") as mock:
        yield mock


@pytest.mark.asyncio
async def test_analyzer_initialization(mock_agent: MagicMock) -> None:
    """Test analyzer initialization."""
    _ = DecisionAnalyzer(model="gemini-test")

    # Check internal agent configuration via mock
    assert mock_agent.call_count == 2

    # Call 1: Single agent
    call1 = mock_agent.mock_calls[0]
    assert call1.kwargs.get("model") == "gemini-test"

    # Call 2: Batch agent
    call2 = mock_agent.mock_calls[1]
    assert call2.kwargs.get("model") == "gemini-test"
    assert call2.kwargs.get("output_type") == BatchDecisionAnalysis


@pytest.mark.asyncio
async def test_analyze_decision_success(mock_agent: MagicMock) -> None:
    """Test successful text analysis."""
    mock_result_data = DecisionAnalysis(
        winner_lawyer_oab="12345",
        winner_lawyer_state="RO",
        winner_party_name="Winner",
        loser_lawyer_oab="67890",
        loser_lawyer_state="RO",
        loser_party_name="Loser",
        decision_type="Sentença",
        outcome=Outcome.WIN,
        summary="Summary of decision",
        judge_name="Judge Dredd",
        decision_reasoning="Law is law",
        confidence_score=0.95,
    )

    mock_run_result = MagicMock()
    mock_run_result.data = mock_result_data

    instance = mock_agent.return_value
    instance.run = AsyncMock(return_value=mock_run_result)

    analyzer = DecisionAnalyzer()
    # Now passing text
    result = await analyzer.analyze_decision("Decision text content...")

    assert result == mock_result_data
    assert instance.run.called


@pytest.mark.asyncio
async def test_analyze_decision_failure(mock_agent: MagicMock) -> None:
    """Test failure handling during analysis."""
    instance = mock_agent.return_value
    instance.run = AsyncMock(side_effect=Exception("API Error"))

    analyzer = DecisionAnalyzer()

    with pytest.raises(Exception, match="API Error"):
        await analyzer.analyze_decision("content")


@pytest.mark.asyncio
async def test_analyze_batch_concurrent_success(mock_agent: MagicMock) -> None:
    """Test successful batch analysis (concurrent)."""
    mock_result_data = DecisionAnalysis(
        winner_lawyer_oab="12345",
        winner_lawyer_state="RO",
        winner_party_name="Winner",
        loser_lawyer_oab="67890",
        loser_lawyer_state="RO",
        loser_party_name="Loser",
        decision_type="Sentença",
        outcome=Outcome.WIN,
        summary="Summary",
        judge_name="Judge",
        decision_reasoning="Reasoning",
        confidence_score=0.9,
    )

    mock_run_result = MagicMock()
    mock_run_result.data = mock_result_data
    instance = mock_agent.return_value
    instance.run = AsyncMock(return_value=mock_run_result)

    analyzer = DecisionAnalyzer()

    # Analyze 2 items (strings now)
    texts = ["decision1", "decision2"]
    results = await analyzer.analyze_batch_concurrent(texts)

    assert len(results) == 2
    assert results[0] == mock_result_data
    assert results[1] == mock_result_data
    assert instance.run.call_count == 2


@pytest.mark.asyncio
async def test_analyze_bulk_success(mock_agent: MagicMock) -> None:
    """Test successful bulk analysis."""
    mock_analysis = DecisionAnalysis(
        winner_lawyer_oab="12345",
        winner_lawyer_state="RO",
        winner_party_name="Winner",
        loser_lawyer_oab="67890",
        loser_lawyer_state="RO",
        loser_party_name="Loser",
        decision_type="Sentença",
        outcome=Outcome.WIN,
        summary="Summary",
        judge_name="Judge",
        decision_reasoning="Reasoning",
        confidence_score=0.9,
    )

    mock_batch_result = BatchDecisionAnalysis(results=[mock_analysis, mock_analysis])

    mock_run_result = MagicMock()
    mock_run_result.data = mock_batch_result

    instance = mock_agent.return_value
    instance.run = AsyncMock(return_value=mock_run_result)

    analyzer = DecisionAnalyzer()

    texts = ["decision1", "decision2"]
    results = await analyzer.analyze_bulk(texts)

    assert len(results) == 2
    assert results[0] == mock_analysis
    assert results[1] == mock_analysis

    # Verify input structure
    call_args = instance.run.call_args
    args = call_args[0][0]  # First arg (user_content list)
    assert len(args) == 7  # 1 intro + 2 * (start + text + end)
    assert "DECISION 1 START" in args[1]
    assert "decision1" in args[2]
