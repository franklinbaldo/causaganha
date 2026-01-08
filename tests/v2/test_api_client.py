"""
TDD for PJe API Client
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from causaganha.v2.api.client import PJeAPIClient

@pytest.mark.asyncio
async def test_client_initialization():
    """Test that client initializes with correct defaults"""
    client = PJeAPIClient()

    assert client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert isinstance(client.client, httpx.AsyncClient)

    await client.close()

@pytest.mark.asyncio
async def test_fetch_intimations_returns_list():
    """Test that fetching returns a list of intimations"""
    client = PJeAPIClient()

    # Mock the API response
    mock_response = {
        "status": "success",
        "count": 0,
        "items": []
    }

    # Setup mock
    mock_get_return = MagicMock()
    mock_get_return.json.return_value = mock_response
    mock_get_return.raise_for_status = MagicMock()

    with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_get_return

        intimations = await client.get_intimations_by_court("TJRO")

        assert isinstance(intimations, list)
        assert len(intimations) == 0

    await client.close()

@pytest.mark.asyncio
async def test_fetch_intimations_pagination():
    """Test pagination logic"""
    client = PJeAPIClient()

    # Mock responses for 2 pages
    page1 = {
        "status": "success",
        "count": 2,
        "items": [{
            "id": 1,
            "numero_processo": "123",
            "data_disponibilizacao": "2024-01-01",
            "siglaTribunal": "TJRO",
            "tipoComunicacao": "Intimação",
            "nomeOrgao": "Vara 1",
            "texto": "text",
            "link": "http://pdf",
            "tipoDocumento": "doc",
            "nomeClasse": "class",
            "hash": "abc",
            "status": "A"
        }]
    }

    page2 = {
        "status": "success",
        "count": 2,
        "items": [{
            "id": 2,
            "numero_processo": "456",
            "data_disponibilizacao": "2024-01-01",
            "siglaTribunal": "TJRO",
            "tipoComunicacao": "Intimação",
            "nomeOrgao": "Vara 1",
            "texto": "text",
            "link": "http://pdf",
            "tipoDocumento": "doc",
            "nomeClasse": "class",
            "hash": "def",
            "status": "A"
        }]
    }

    # Setup mock to return page1 then page2 then empty items (stop condition)
    # The client checks "count" vs total fetched.
    # Logic:
    # 1. Fetch page 1. items=1. total=1. count=2. 1 < 2 -> continue.
    # 2. Fetch page 2. items=1. total=2. count=2. 2 >= 2 -> break.

    mock_get_return1 = MagicMock()
    mock_get_return1.json.return_value = page1

    mock_get_return2 = MagicMock()
    mock_get_return2.json.return_value = page2

    with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_get_return1, mock_get_return2]

        intimations = await client.get_intimations_by_court("TJRO", limit_per_page=1)

        assert len(intimations) == 2
        assert intimations[0].id == 1
        assert intimations[1].id == 2
        assert mock_get.call_count == 2

    await client.close()
