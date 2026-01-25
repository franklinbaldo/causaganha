"""Tests for the PJe API Client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from causaganha.clients.pje import Intimation, PJeAPIClient


@pytest.fixture
def api_client() -> PJeAPIClient:
    """Fixture for PJeAPIClient."""
    return PJeAPIClient()


@pytest.mark.asyncio
async def test_client_initialization() -> None:
    """Test that client initializes with correct defaults."""
    client = PJeAPIClient()
    assert client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert isinstance(client.client, httpx.AsyncClient)
    await client.close()


@pytest.mark.asyncio
async def test_get_intimations_by_court_success(api_client: PJeAPIClient) -> None:
    """Test fetching intimations successfully."""
    # Mock response data
    mock_data = {
        "items": [
            {
                "id": 1,
                "numero_processo": "0000001-00.2024.8.22.0001",
                "data_disponibilizacao": "2024-01-01",
                "siglaTribunal": "TJRO",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara 1",
                "texto": "Texto",
                "link": "http://pdf",
                "tipoDocumento": "Despacho",
                "nomeClasse": "Procedimento Comum",
                "hash": "hash1",
                "status": "P",
                "destinatarioadvogados": [],
                "destinatarios": [],
            },
        ],
        "count": 1,
    }

    # Mock the HTTP client's get method
    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        intimations = await api_client.get_intimations_by_court("TJRO")

        assert len(intimations) == 1
        assert isinstance(intimations[0], Intimation)
        assert intimations[0].id == 1
        assert intimations[0].sigla_tribunal == "TJRO"

        # Verify calls
        mock_get.assert_called()


@pytest.mark.asyncio
async def test_get_intimations_pagination(api_client: PJeAPIClient) -> None:
    """Test pagination logic."""
    # Mock responses for 2 pages
    total_items = 150

    page1_data = {
        "items": [
            {
                "id": i,
                "numero_processo": "proc",
                "data_disponibilizacao": "2024-01-01",
                "siglaTribunal": "TJRO",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara",
                "texto": "txt",
                "link": "url",
                "tipoDocumento": "doc",
                "nomeClasse": "cls",
                "hash": f"h{i}",
                "status": "P",
            } for i in range(1, 101)
        ],
        "count": total_items,
    }
    page2_data = {
        "items": [
            {
                "id": i,
                "numero_processo": "proc",
                "data_disponibilizacao": "2024-01-01",
                "siglaTribunal": "TJRO",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara",
                "texto": "txt",
                "link": "url",
                "tipoDocumento": "doc",
                "nomeClasse": "cls",
                "hash": f"h{i}",
                "status": "P",
            } for i in range(101, 151)
        ],
        "count": total_items,
    }

    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        # Side effect for consecutive calls
        mock_response1 = MagicMock()
        mock_response1.json.return_value = page1_data
        mock_response1.raise_for_status.return_value = None

        mock_response2 = MagicMock()
        mock_response2.json.return_value = page2_data
        mock_response2.raise_for_status.return_value = None

        mock_get.side_effect = [mock_response1, mock_response2]

        intimations = await api_client.get_intimations_by_court("TJRO")

        assert len(intimations) == total_items
        assert mock_get.call_count == 2  # noqa: PLR2004


@pytest.mark.asyncio
async def test_get_intimations_error(api_client: PJeAPIClient) -> None:
    """Test error handling."""
    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("API Error")

        with pytest.raises(httpx.HTTPError):
            await api_client.get_intimations_by_court("TJRO")
