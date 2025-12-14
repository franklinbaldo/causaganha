import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from causaganha.analysis.analyzer import DecisionAnalyzer
from causaganha.analysis.models import DecisionAnalysis, Outcome


@pytest.mark.asyncio
async def test_analyze_decision_success():
    # Set dummy API key to pass pydantic-ai validation
    os.environ["GOOGLE_API_KEY"] = "dummy_key"

    mock_result = DecisionAnalysis(
        outcome=Outcome.WIN,
        summary="The court ruled in favor of the plaintiff.",
        judge_name="Judge Dredd",
        confidence_score=0.95,
        winner_lawyer_oab="12345",
        winner_lawyer_state="RO",
        winner_party_name="Winner Inc",
        loser_lawyer_oab="67890",
        loser_lawyer_state="RO",
        loser_party_name="Loser Ltd",
        decision_type="Sentença",
        decision_reasoning="Reasoning...",
    )

    analyzer = DecisionAnalyzer(model="google-gla:gemini-2.5-flash")

    # Mock the agent's run method
    analyzer.agent = AsyncMock()
    # The run method returns a RunResult object, which has a .data attribute
    analyzer.agent.run.return_value = MagicMock(data=mock_result)

    pdf_content = b"%PDF-1.5..."

    result = await analyzer.analyze_decision(pdf_content)

    assert isinstance(result, DecisionAnalysis)
    assert result.outcome == Outcome.WIN
    assert result.summary == "The court ruled in favor of the plaintiff."
    assert result.judge_name == "Judge Dredd"

    assert analyzer.agent.run.call_count == 1

    # Clean up
    del os.environ["GOOGLE_API_KEY"]
