"""Unit tests for PJe API Client
"""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date
import httpx
import pytest

from causaganha.api.client import PJeAPIClient
from tests.conftest import create_mock_intimation_item


@pytest.mark.asyncio
async def test_client_initialization() -> None:
    """Test that client initializes with correct defaults"""
    client = PJeAPIClient()

    assert client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert client.client is not None
    assert isinstance(client.client, httpx.AsyncClient)

    await client.close()

@pytest.mark.asyncio
async def test_fetch_intimations_returns_list(api_client: PJeAPIClient) -> None:
    """Test that fetching returns a list of intimations"""
    mock_response = {
        "status": "success",
        "count": 0,
        "items": [],
    }

    # Mock the request
    with patch.object(api_client.client, "request", new_callable=AsyncMock) as mock_request:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None
        mock_request.return_value = mock_resp

        intimations = await api_client.get_intimations_by_court("TJRO")

        assert isinstance(intimations, list)
        assert len(intimations) == 0


@pytest.mark.asyncio
async def test_fetch_intimations_success(api_client: PJeAPIClient) -> None:
    """Test API fetch with mocked HTTP response"""
    mock_response = {
        "status": "success",
        "count": 1,
        "items": [create_mock_intimation_item(123456)],
    }

    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        intimations = await api_client.get_intimations_by_court("TJRO")

        assert len(intimations) == 1
        assert intimations[0].id == 123456
        assert intimations[0].sigla_tribunal == "TJRO"


@pytest.mark.asyncio
async def test_fetch_intimations_pagination(api_client: PJeAPIClient) -> None:
    """Test pagination"""
    page1_response = {"status": "success", "count": 2, "items": [create_mock_intimation_item(1)]}
    page2_response = {"status": "success", "count": 2, "items": [create_mock_intimation_item(2)]}
    empty_response = {"status": "success", "count": 2, "items": []}

    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_resp1 = MagicMock()
        mock_resp1.json.return_value = page1_response
        mock_resp1.raise_for_status.return_value = None

        mock_resp2 = MagicMock()
        mock_resp2.json.return_value = page2_response
        mock_resp2.raise_for_status.return_value = None

        mock_resp3 = MagicMock()
        mock_resp3.json.return_value = empty_response
        mock_resp3.raise_for_status.return_value = None

        mock_get.side_effect = [mock_resp1, mock_resp2, mock_resp3]

        intimations = await api_client.get_intimations_by_court("TJRO", itens_por_pagina=1)

        assert len(intimations) == 2
        assert intimations[0].id == 1
        assert intimations[1].id == 2
        assert mock_get.call_count == 3

@pytest.mark.asyncio
async def test_fetch_raises_on_http_error(api_client: PJeAPIClient) -> None:
    """Test error handling"""
    # For client.request used in get_intimations_by_court if using .get
    # If using .get, we mock .get. If using .request, we mock .request.
    # The current implementation uses self.client.get

    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network error")

        with pytest.raises(httpx.HTTPError):
            await api_client.get_intimations_by_court("TJRO")

@pytest.mark.asyncio
async def test_fetch_intimations_with_dates(api_client: PJeAPIClient) -> None:
    """Test fetching with date parameters"""
    mock_response = {
        "status": "success",
        "count": 0,
        "items": [],
    }

    start_date = date(2024, 1, 1)
    end_date = date(2024, 1, 31)

    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        await api_client.get_intimations_by_court(
            "TJRO",
            data_disponibilizacao_inicio=start_date,
            data_disponibilizacao_fim=end_date
        )

        call_args = mock_get.call_args
        assert call_args is not None
        params = call_args.kwargs["params"]
        assert params["dataDisponibilizacaoInicio"] == "2024-01-01"
        assert params["dataDisponibilizacaoFim"] == "2024-01-31"

@pytest.mark.asyncio
async def test_fetch_intimations_validation_error(api_client: PJeAPIClient) -> None:
    """Test handling of validation errors"""
    # Item with missing required field (id)
    invalid_item = create_mock_intimation_item(1)
    del invalid_item["id"]

    mock_response = {
        "status": "success",
        "count": 1,
        "items": [invalid_item],
    }

    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        # Should raise validation error (which propagates as Exception or ValidationError from pydantic)
        with pytest.raises(Exception): # Pydantic ValidationError
            await api_client.get_intimations_by_court("TJRO")
