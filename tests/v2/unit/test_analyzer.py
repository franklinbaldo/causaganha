"""Unit tests for Decision Analyzer."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from causaganha.analysis.analyzer import DecisionAnalyzer
from causaganha.analysis.models import DecisionAnalysis, Outcome


@pytest.fixture
def mock_agent() -> Generator[MagicMock, None, None]:
    with patch("causaganha.analysis.analyzer.Agent") as mock:
        yield mock


@pytest.mark.asyncio
async def test_analyzer_initialization(mock_agent: MagicMock) -> None:
    """Test analyzer initialization."""
    # Use 'model' parameter instead of 'model_name' as per implementation
    _ = DecisionAnalyzer(model="gemini-test")

    # Check internal agent configuration via mock
    mock_agent.assert_called_once()
    call_args = mock_agent.call_args
    assert call_args.kwargs.get("model") == "gemini-test"

    # Verify system prompt contains critical instructions
    system_prompt = call_args.kwargs.get("system_prompt", "")
    # The current prompt is: "...Identify the winning and losing parties..."
    assert "winning" in system_prompt.lower()
    assert "losing" in system_prompt.lower()
    assert "oab" in system_prompt.lower()


@pytest.mark.asyncio
async def test_analyze_decision_success(mock_agent: MagicMock) -> None:
    """Test successful PDF analysis."""
    # Mock result matching the model definition
    # Note: Outcome is an Enum

    mock_result_data = DecisionAnalysis(
        winner_lawyer_oab="12345",
        winner_lawyer_state="RO",
        winner_party_name="Winner",
        loser_lawyer_oab="67890",
        loser_lawyer_state="RO",
        loser_party_name="Loser",
        decision_type="Sentença",
        outcome=Outcome.WIN,  # Using Enum
        summary="Summary of decision",  # Required field
        judge_name="Judge Dredd",
        decision_reasoning="Law is law",
        confidence_score=0.95,
    )

    # Setup mock agent run return
    mock_run_result = MagicMock()
    mock_run_result.data = mock_result_data

    instance = mock_agent.return_value
    instance.run = AsyncMock(return_value=mock_run_result)

    analyzer = DecisionAnalyzer()
    # Using analyze_decision with bytes instead of analyze_pdf with url
    result = await analyzer.analyze_decision(b"fake pdf content")

    assert result == mock_result_data
    instance.run.assert_called_once()

    # Check if BinaryContent is passed
    # This requires checking arguments structure which is a list [prompt, BinaryContent]
    call_args = instance.run.call_args
    args = call_args[0][0]  # The first argument to run() is the messages list
    assert isinstance(args, list)
    assert len(args) == 2


@pytest.mark.asyncio
async def test_analyze_decision_failure(mock_agent: MagicMock) -> None:
    """Test failure handling during analysis."""
    instance = mock_agent.return_value
    instance.run = AsyncMock(side_effect=Exception("API Error"))

    analyzer = DecisionAnalyzer()

    with pytest.raises(Exception, match="API Error"):
        await analyzer.analyze_decision(b"content")


@pytest.mark.asyncio
async def test_analyze_batch_placeholder(mock_agent: MagicMock) -> None:
    """Test batch analysis.

    Note: batch analysis is NOT yet implemented in DecisionAnalyzer class in this file version,
    but it was in the plan. I will skip this test or remove it until implemented.
    The current implementation only has `analyze_decision`.
    """
