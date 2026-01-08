"""
TDD for Pydantic AI Analyzer
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from causaganha.v2.analysis.analyzer import DecisionAnalyzer
from causaganha.v2.analysis.models import DecisionAnalysis

@pytest.fixture
def mock_agent():
    with patch('causaganha.v2.analysis.analyzer.Agent') as mock:
        yield mock

@pytest.mark.asyncio
async def test_analyzer_initialization(mock_agent):
    """Test analyzer initialization"""
    analyzer = DecisionAnalyzer()

    mock_agent.assert_called_once()
    assert analyzer.model_name == "gemini-2.5-flash"
    assert analyzer.provider == "google-gla"

@pytest.mark.asyncio
async def test_analyze_pdf_success(mock_agent):
    """Test successful PDF analysis"""
    # Mock return value
    expected_result = DecisionAnalysis(
        winner_lawyer_oab="123",
        winner_lawyer_state="RO",
        winner_party_name="Winner",
        loser_lawyer_oab="456",
        loser_lawyer_state="RO",
        loser_party_name="Loser",
        decision_type="sentença",
        outcome="procedente",
        judge_name="Judge",
        decision_reasoning="Reason",
        confidence_score=0.9
    )

    # Setup mock agent run
    mock_instance = mock_agent.return_value
    mock_run_result = MagicMock()
    mock_run_result.data = expected_result
    mock_instance.run = AsyncMock(return_value=mock_run_result)

    analyzer = DecisionAnalyzer()

    # Mock httpx for PDF download
    with patch('httpx.AsyncClient') as mock_client:
        mock_get_response = MagicMock()
        mock_get_response.content = b"pdf content"
        mock_get_response.raise_for_status = MagicMock()

        mock_client_instance = mock_client.return_value.__aenter__.return_value
        mock_client_instance.get.return_value = mock_get_response

        result = await analyzer.analyze_pdf("http://pdf")

    assert result == expected_result
    mock_instance.run.assert_called_once()

@pytest.mark.asyncio
async def test_analyze_batch_success(mock_agent):
    """Test batch analysis"""
    analyzer = DecisionAnalyzer()

    # Mock return value
    expected_result = DecisionAnalysis(
        winner_lawyer_oab="123",
        winner_lawyer_state="RO",
        winner_party_name="Winner",
        loser_lawyer_oab="456",
        loser_lawyer_state="RO",
        loser_party_name="Loser",
        decision_type="sentença",
        outcome="procedente",
        judge_name="Judge",
        decision_reasoning="Reason",
        confidence_score=0.9
    )

    # Mock analyze_pdf instead of internal agent to test batch logic simply
    with patch.object(analyzer, 'analyze_pdf') as mock_analyze:
        mock_analyze.return_value = expected_result # Return a valid DecisionAnalysis object

        urls = ["http://1", "http://2"]
        results = await analyzer.analyze_batch(urls)

        assert len(results) == 2
        assert mock_analyze.call_count == 2
