"""Unit tests for PJe API Client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from causaganha.integrations.pje.client import PJeAPIClient
from tests.conftest import create_mock_intimation_item


@pytest.mark.asyncio
async def test_client_initialization() -> None:
    """Test that client initializes with correct defaults."""
    client = PJeAPIClient()

    assert client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert client.client is not None
    assert isinstance(client.client, httpx.AsyncClient)

    await client.close()

@pytest.mark.asyncio
async def test_fetch_intimations_returns_list(api_client: PJeAPIClient) -> None:
    """Test that fetching returns a list of intimations."""
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
    """Test API fetch with mocked HTTP response."""
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
    """Test pagination."""
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
    """Test error handling."""
    with patch.object(api_client.client, "request", new_callable=AsyncMock) as mock_request:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPError("Network error")
        mock_request.return_value = mock_resp

        with pytest.raises(httpx.HTTPError):
            await api_client.get_intimations_by_court("TJRO")
