"""Unit tests for PJe API Client."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from causaganha.api.client import PJeAPIClient
from causaganha.domain.models import Intimation as DomainIntimation
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
    item = create_mock_intimation_item(123456)
    # Add complex lawyer/party data to test mapping
    item["destinatarios"] = [{"nome": "Party A", "polo": "A"}]
    item["destinatarioadvogados"] = [{
        "advogado": {
            "id": 1,
            "nome": "Lawyer A",
            "numero_oab": "123",
            "uf_oab": "SP"
        }
    }]

    mock_response = {
        "status": "success",
        "count": 1,
        "items": [item],
    }

    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        intimations = await api_client.get_intimations_by_court("TJRO")

        assert len(intimations) == 1
        obj = intimations[0]
        assert isinstance(obj, DomainIntimation)
        assert obj.id == 123456
        assert obj.sigla_tribunal == "TJRO"

        # Verify nested mapping
        assert len(obj.partes) == 1
        assert obj.partes[0].nome == "Party A"

        assert len(obj.advogados) == 1
        assert obj.advogados[0].nome == "Lawyer A"


@pytest.mark.asyncio
async def test_fetch_intimations_pagination(api_client: PJeAPIClient) -> None:
    """Test pagination."""
    page1_response = {"status": "success", "count": 2, "items": [create_mock_intimation_item(1)]}
    page2_response = {"status": "success", "count": 2, "items": [create_mock_intimation_item(2)]}
    # Page 3 empty means stop
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

        # Simulate:
        # 1. Page 1 returns 1 item (asked for 1) -> continue
        # 2. Page 2 returns 1 item (asked for 1) -> continue
        # 3. Page 3 returns empty -> break
        mock_get.side_effect = [mock_resp1, mock_resp2, mock_resp3]

        intimations = await api_client.get_intimations_by_court("TJRO", itens_por_pagina=1)

        assert len(intimations) == 2
        assert intimations[0].id == 1
        assert intimations[1].id == 2
        assert mock_get.call_count == 3

@pytest.mark.asyncio
async def test_fetch_intimations_pagination_partial_page(api_client: PJeAPIClient) -> None:
    """Test pagination stops if less items than requested."""
    # Requested 100, got 1. Should stop immediately.
    page1_response = {"status": "success", "count": 1, "items": [create_mock_intimation_item(1)]}

    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_resp1 = MagicMock()
        mock_resp1.json.return_value = page1_response
        mock_resp1.raise_for_status.return_value = None
        mock_get.return_value = mock_resp1

        intimations = await api_client.get_intimations_by_court("TJRO", itens_por_pagina=100)

        assert len(intimations) == 1
        assert mock_get.call_count == 1 # Only one call needed

@pytest.mark.asyncio
async def test_fetch_raises_on_http_error(api_client: PJeAPIClient) -> None:
    """Test error handling."""
    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network error")

        with pytest.raises(httpx.HTTPError):
            await api_client.get_intimations_by_court("TJRO")

@pytest.mark.asyncio
async def test_fetch_with_date_filters(api_client: PJeAPIClient) -> None:
    """Test date filtering params."""
    mock_response = {"status": "success", "count": 0, "items": []}

    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_get.return_value = mock_resp

        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        await api_client.get_intimations_by_court(
            "TJRO",
            data_disponibilizacao_inicio=start,
            data_disponibilizacao_fim=end
        )

        args, kwargs = mock_get.call_args
        params = kwargs["params"]
        assert params["dataDisponibilizacaoInicio"] == "2024-01-01"
        assert params["dataDisponibilizacaoFim"] == "2024-01-31"

@pytest.mark.asyncio
async def test_fetch_validation_error(api_client: PJeAPIClient) -> None:
    """Test that schema validation failure raises exception."""
    # Missing required fields
    invalid_item = {"id": 123}
    mock_response = {"status": "success", "count": 1, "items": [invalid_item]}

    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_get.return_value = mock_resp

        with pytest.raises(Exception): # ValidationError wrapped or raw
            await api_client.get_intimations_by_court("TJRO")
