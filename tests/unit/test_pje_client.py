"""Unit tests for PJe API Client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from causaganha.clients.pje import Intimation, PJeAPIClient


@pytest.fixture
async def api_client():
    """Provide a clean API client for tests."""
    client = PJeAPIClient()
    yield client
    await client.close()

@pytest.mark.asyncio
async def test_client_initialization(api_client):
    """Test that client initializes with correct defaults."""
    assert api_client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert isinstance(api_client.client, httpx.AsyncClient)

@pytest.mark.asyncio
async def test_fetch_intimations_success(api_client):
    """Test API fetch with mocked HTTP response."""
    mock_response = {
        "status": "success",
        "count": 1,
        "items": [
            {
                "id": 123,
                "numero_processo": "0001234-56.2024.8.22.0001",
                "data_disponibilizacao": "2024-12-01",
                "siglaTribunal": "TJRO",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara Cível",
                "texto": "Decisão...",
                "link": "https://example.com/doc.pdf",
                "tipoDocumento": "Decisão",
                "nomeClasse": "Procedimento Comum",
                "hash": "abc123hash",
                "status": "D",
                "destinatarioadvogados": [],
                "destinatarios": []
            }
        ]
    }

    # Mock the response.json() and raise_for_status()
    mock_resp_obj = MagicMock()
    mock_resp_obj.json.return_value = mock_response
    mock_resp_obj.raise_for_status.return_value = None

    # Patch the client.get method
    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp_obj

        intimations = await api_client.get_intimations_by_court("TJRO")

        assert len(intimations) == 1
        assert isinstance(intimations[0], Intimation)
        assert intimations[0].id == 123
        assert intimations[0].sigla_tribunal == "TJRO"

        # Verify call arguments
        mock_get.assert_called_once()
        _args, kwargs = mock_get.call_args
        assert kwargs["params"]["siglaTribunal"] == "TJRO"

@pytest.mark.asyncio
async def test_fetch_intimations_pagination(api_client):
    """Test that fetching handles pagination."""
    # Page 1
    page1 = {
        "status": "success",
        "count": 105,
        "items": [
            {
                "id": i,
                "numero_processo": f"proc{i}",
                "data_disponibilizacao": "2024-01-01",
                "siglaTribunal": "TJRO",
                "tipoComunicacao": "I",
                "nomeOrgao": "O",
                "texto": "T",
                "link": "L",
                "tipoDocumento": "D",
                "nomeClasse": "C",
                "hash": f"h{i}",
                "status": "S"
            } for i in range(100)
        ]
    }
    # Page 2
    page2 = {
        "status": "success",
        "count": 105,
        "items": [
            {
                "id": i,
                "numero_processo": f"proc{i}",
                "data_disponibilizacao": "2024-01-01",
                "siglaTribunal": "TJRO",
                "tipoComunicacao": "I",
                "nomeOrgao": "O",
                "texto": "T",
                "link": "L",
                "tipoDocumento": "D",
                "nomeClasse": "C",
                "hash": f"h{i}",
                "status": "S"
            } for i in range(100, 105)
        ]
    }

    mock_resp1 = MagicMock()
    mock_resp1.json.return_value = page1
    mock_resp1.raise_for_status.return_value = None

    mock_resp2 = MagicMock()
    mock_resp2.json.return_value = page2
    mock_resp2.raise_for_status.return_value = None

    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_resp1, mock_resp2]

        intimations = await api_client.get_intimations_by_court("TJRO")

        assert len(intimations) == 105
        assert mock_get.call_count == 2

        # Verify offsets
        call1_kwargs = mock_get.call_args_list[0][1]
        call2_kwargs = mock_get.call_args_list[1][1]
        assert call1_kwargs["params"]["offset"] == 0
        assert call2_kwargs["params"]["offset"] == 100

@pytest.mark.asyncio
async def test_fetch_intimations_http_error(api_client):
    """Test error handling when API fails."""
    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("API Down")

        with pytest.raises(httpx.HTTPError):
            await api_client.get_intimations_by_court("TJRO")
