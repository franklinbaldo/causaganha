from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from causaganha.analysis.analyzer import DecisionAnalyzer
from causaganha.analysis.models import DecisionAnalysis


@pytest.fixture
def mock_agent() -> Generator[AsyncMock, None, None]:
    with patch("causaganha.analysis.analyzer.Agent") as mock_agent_cls:
        instance = mock_agent_cls.return_value

        # Setup run return value as an awaitable
        async def mock_run(*args, **kwargs) -> AsyncMock:
            mock_result = AsyncMock()
            mock_result.data = DecisionAnalysis(
                winner_lawyer_oab="12345",
                winner_lawyer_state="RO",
                winner_party_name="Winner",
                loser_lawyer_oab="67890",
                loser_lawyer_state="RO",
                loser_party_name="Loser",
                decision_type="sentenca",
                outcome="procedente",
                judge_name="Judge",
                decision_reasoning="Reason",
                confidence_score=0.9,
            )
            return mock_result

        instance.run.side_effect = mock_run
        yield instance


@pytest.mark.asyncio
async def test_analyze_pdf_success(mock_agent: AsyncMock) -> None:
    analyzer = DecisionAnalyzer()
    result = await analyzer.analyze_pdf("http://pdf")

    assert result.winner_lawyer_oab == "12345"
    assert result.confidence_score == 0.9

    # Verify call
    mock_agent.run.assert_called()
