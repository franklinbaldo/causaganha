import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from causaganha.v2.analysis.analyzer import DecisionAnalyzer, BinaryContent
from causaganha.v2.analysis.models import DecisionAnalysis

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy_key")

@pytest.mark.asyncio
async def test_analyzer_initialization():
    analyzer = DecisionAnalyzer()
    assert analyzer.model_name == "gemini-1.5-flash"
    assert analyzer.provider == "google-gla"
    assert analyzer.agent is not None

@pytest.mark.asyncio
async def test_analyze_pdf_success():
    analyzer = DecisionAnalyzer()

    # Mock response
    mock_result = DecisionAnalysis(
        winner_lawyer_oab="5733",
        winner_lawyer_state="RO",
        winner_party_name="Winner",
        loser_lawyer_oab="6789",
        loser_lawyer_state="RO",
        loser_party_name="Loser",
        decision_type="sentença",
        outcome="procedente",
        judge_name="Judge",
        decision_reasoning="Reasoning",
        confidence_score=0.95
    )

    # Mock Agent.run
    mock_run_result = MagicMock()
    mock_run_result.data = mock_result

    # Mock httpx and agent.run
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch.object(analyzer.agent, 'run', new_callable=AsyncMock) as mock_run:

        # Setup httpx mock
        mock_resp = MagicMock()
        mock_resp.content = b"%PDF-1.4..."
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        # Setup run mock
        mock_run.return_value = mock_run_result

        result = await analyzer.analyze_pdf("http://example.com/doc.pdf", intimation_id=123)

        assert result == mock_result
        mock_run.assert_called_once()

        # Verify BinaryContent was passed
        args = mock_run.call_args[0]
        content_list = args[0]
        assert isinstance(content_list, list)
        # Should be [prompt_str, BinaryContent]
        assert isinstance(content_list[1], BinaryContent)
        assert content_list[1].data == b"%PDF-1.4..."

@pytest.mark.asyncio
async def test_analyze_batch_success():
    analyzer = DecisionAnalyzer()

    mock_result = DecisionAnalysis(
        winner_lawyer_oab="5733",
        winner_lawyer_state="RO",
        winner_party_name="Winner",
        loser_lawyer_oab="6789",
        loser_lawyer_state="RO",
        loser_party_name="Loser",
        decision_type="sentença",
        outcome="procedente",
        judge_name="Judge",
        decision_reasoning="Reasoning",
        confidence_score=0.95
    )

    # Use patch to mock analyze_pdf method
    with patch.object(analyzer, 'analyze_pdf', new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = mock_result

        urls = ["http://a.pdf", "http://b.pdf"]
        ids = [1, 2]

        results = await analyzer.analyze_batch(urls, ids)

        assert len(results) == 2
        assert mock_analyze.call_count == 2
