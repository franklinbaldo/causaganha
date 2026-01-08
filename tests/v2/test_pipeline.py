"""
TDD for Pipeline
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from causaganha.v2.pipeline.collect import collect_metadata_for_court
from causaganha.v2.pipeline.analyze import analyze_pending_decisions
from causaganha.v2.pipeline.score import calculate_ratings

@pytest.mark.asyncio
async def test_collect_metadata_success():
    """Test successful metadata collection"""

    # Mock dependencies
    with patch('causaganha.v2.pipeline.collect.PJeAPIClient') as mock_client_cls:
        with patch('causaganha.v2.pipeline.collect.get_connection') as mock_conn:
            with patch('causaganha.v2.pipeline.collect.store_intimations') as mock_store:
                with patch('causaganha.v2.pipeline.collect.store_lawyer_associations') as mock_store_lawyers:

                    # Setup mocks
                    mock_client = mock_client_cls.return_value
                    mock_client.get_intimations_by_court = AsyncMock(return_value=[
                        MagicMock(id=1, destinatarioadvogados=[])
                    ])
                    mock_client.close = AsyncMock()

                    mock_store.return_value = 1
                    mock_store_lawyers.return_value = 0

                    result = await collect_metadata_for_court("TJRO")

                    assert result['status'] == 'success'
                    assert result['intimations_new'] == 1
                    mock_client.get_intimations_by_court.assert_called_once()
                    mock_store.assert_called_once()

@pytest.mark.asyncio
async def test_analyze_pending_decisions_success():
    """Test successful analysis pipeline"""

    with patch('causaganha.v2.pipeline.analyze.get_connection') as mock_conn:
        with patch('causaganha.v2.pipeline.analyze.DecisionAnalyzer') as mock_analyzer_cls:
            with patch('causaganha.v2.pipeline.analyze.get_unanalyzed_intimations') as mock_get_pending:
                with patch('causaganha.v2.pipeline.analyze._store_analysis') as mock_store:
                    with patch('causaganha.v2.pipeline.analyze._mark_as_analyzed') as mock_mark:

                        # Setup mocks
                        mock_get_pending.side_effect = [
                            [{'id': 1, 'link': 'http://pdf'}], # First batch
                            [] # No more pending
                        ]

                        mock_analyzer = mock_analyzer_cls.return_value
                        mock_analyzer.analyze_batch = AsyncMock(return_value=[
                            MagicMock(winner_lawyer_oab="123")
                        ])

                        result = await analyze_pending_decisions(batch_size=1)

                        assert result['status'] == 'success'
                        assert result['analyzed'] == 1
                        mock_get_pending.assert_called()
                        mock_analyzer.analyze_batch.assert_called_once()
                        mock_store.assert_called_once()
                        mock_mark.assert_called_once()

@pytest.mark.asyncio
async def test_calculate_ratings_success():
    """Test successful rating calculation"""

    with patch('causaganha.v2.pipeline.score.get_connection') as mock_conn:
        # Simple test for the placeholder implementation
        result = await calculate_ratings()
        assert result['status'] == 'success'
