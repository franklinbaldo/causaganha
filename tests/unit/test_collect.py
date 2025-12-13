import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from causaganha.pipeline.collect import collect_metadata_for_court

@pytest.mark.asyncio
async def test_collect_metadata_success() -> None:
    with patch("causaganha.pipeline.collect.PJeAPIClient") as mock_client_cls, \
         patch("causaganha.pipeline.collect.store_intimations") as mock_store, \
         patch("causaganha.pipeline.collect.store_lawyer_associations") as mock_store_lawyers, \
         patch("causaganha.pipeline.collect.get_connection"):

        client_instance = mock_client_cls.return_value

        mock_intimation = MagicMock()
        mock_intimation.id = 1
        mock_intimation.destinatarioadvogados = []

        # Fix: Ensure async methods are AsyncMock
        client_instance.get_intimations_by_court = AsyncMock(return_value=[mock_intimation])
        client_instance.close = AsyncMock()

        mock_store.return_value = 1
        mock_store_lawyers.return_value = 0

        result = await collect_metadata_for_court("TJRO")

        assert result['status'] == 'success'
        assert result['intimations_fetched'] == 1
        assert result['intimations_processed'] == 1

        client_instance.get_intimations_by_court.assert_called_once()
        client_instance.close.assert_called_once()
