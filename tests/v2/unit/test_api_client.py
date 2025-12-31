"""Unit tests for the PJe API Client.

These tests mock external dependencies to test logic, not the network.
"""

from unittest.mock import patch

import httpx
import pytest

from causaganha.v2.api.client import PJeAPIClient


@pytest.mark.asyncio
async def test_client_initializes_with_defaults() -> None:
    """Test that client initializes with correct defaults."""
    client = PJeAPIClient()

    assert client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert client.client is not None
    assert isinstance(client.client, httpx.AsyncClient)

    await client.close()


@pytest.mark.asyncio
async def test_fetch_intimations_returns_list(api_client: PJeAPIClient) -> None:
    """Test that fetching returns a list of intimations."""
    # Mock the API response
    mock_response = {
        "status": "success",
        "count": 0,
        "items": [],
    }

    with patch.object(api_client.client, "get") as mock_get:
        mock_get.return_value = httpx.Response(
            200,
            json=mock_response,
            request=httpx.Request("GET", "https://example.com"),
        )

        intimations = await api_client.get_intimations_by_court("TJRO")

        assert isinstance(intimations, list)
        assert len(intimations) == 0


@pytest.mark.asyncio
async def test_fetch_intimations_success(api_client: PJeAPIClient) -> None:
    """Test API fetch with mocked HTTP response."""
    mock_response = {
        "status": "success",
        "count": 1,
        "items": [
            {
                "id": 123456,
                "numero_processo": "0001234-56.2024.8.22.0001",
                "numeroprocessocommascara": "0001234-56.2024.8.22.0001",
                "data_disponibilizacao": "2024-12-01",
                "siglaTribunal": "TJRO",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara Cível",
                "texto": "Decisão...",
                "link": "https://example.com/doc.pdf",
                "tipoDocumento": "Decisão",
                "nomeClasse": "Procedimento Comum",
                "hash": "abc123456",
                "status": "D",
            },
        ],
    }

    with patch.object(api_client.client, "get") as mock_get:
        mock_get.return_value = httpx.Response(
            200,
            json=mock_response,
            request=httpx.Request("GET", "https://example.com"),
        )

        intimations = await api_client.get_intimations_by_court("TJRO")

        assert len(intimations) == 1
        assert intimations[0].id == 123456
        assert intimations[0].sigla_tribunal == "TJRO"


@pytest.mark.asyncio
async def test_fetch_raises_on_http_error(api_client: PJeAPIClient) -> None:
    """Test error handling with mocked HTTP error."""
    with patch.object(api_client.client, "get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network error")

        with pytest.raises(httpx.HTTPError):
            await api_client.get_intimations_by_court("TJRO")
