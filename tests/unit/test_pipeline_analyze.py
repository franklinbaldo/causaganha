import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from causaganha.pipeline.analyze import analyze_pending_decisions

@pytest.mark.asyncio
async def test_analyze_pending_success() -> None:
    with patch("causaganha.pipeline.analyze.DecisionAnalyzer") as mock_analyzer_cls, \
         patch("causaganha.pipeline.analyze.get_unanalyzed_intimations") as mock_get_pending, \
         patch("causaganha.pipeline.analyze._store_analysis") as mock_store, \
         patch("causaganha.pipeline.analyze._mark_as_analyzed") as mock_mark, \
         patch("causaganha.pipeline.analyze.get_connection"):

        analyzer_instance = mock_analyzer_cls.return_value

        # Mock pending items: return list first time, then empty list
        mock_get_pending.side_effect = [
            [{"id": 1, "link": "http://pdf1"}, {"id": 2, "link": "http://pdf2"}],
            [],
        ]

        # Mock analyze_batch
        mock_analysis1 = MagicMock(winner_lawyer_oab="123", confidence_score=0.9)
        mock_analysis2 = MagicMock(winner_lawyer_oab="456", confidence_score=0.8)

        analyzer_instance.analyze_batch = AsyncMock(return_value=[
            mock_analysis1,
            mock_analysis2,
        ])

        result = await analyze_pending_decisions(batch_size=2)

        assert result["analyzed"] == 2
        assert result["status"] == "success"

        analyzer_instance.analyze_batch.assert_called()
        assert mock_store.call_count == 2
        assert mock_mark.call_count == 2
