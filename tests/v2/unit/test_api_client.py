"""TDD Example: Building the PJe API Client.

Each test is written before the implementation.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from causaganha.v2.api.client import PJeAPIClient


# TEST 1: Client initialization
@pytest.mark.asyncio
async def test_client_initializes_with_defaults() -> None:
    """RED → GREEN → REFACTOR.

    This test is written FIRST, before PJeAPIClient exists.
    """
    client = PJeAPIClient()

    assert client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert client.client is not None

    await client.close()


# TEST 2: Fetching returns list of domain objects
@pytest.mark.asyncio
async def test_fetch_intimations_returns_list(api_client: PJeAPIClient) -> None:
    """Test that fetching returns a list of Domain Objects.

    This test verifies that the client fetches data and converts it
    to domain objects.
    """
    mock_response_data = {
        "status": "success",
        "count": 1,
        "items": [
            {
                "id": 123,
                "numero_processo": "0001234-56.2024.8.22.0001",
                "siglaTribunal": "TJRO",
                "data_disponibilizacao": "2024-01-01",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara Cível",
                "texto": "Texto da intimação",
                "link": "http://example.com/pdf",
                "tipoDocumento": "Despacho",
                "nomeClasse": "Procedimento Comum",
                "hash": "abc123hash",
                "status": "P",
            },
        ],
    }

    # Create a MagicMock for the response object (not AsyncMock)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status.return_value = None

    # Patch the get method of the client
    with patch.object(api_client.client, "get") as mock_get:
        # The mock_get is an AsyncMock because client.get is async.
        # Its return_value (what you get when you await it) should be our mock_response.
        mock_get.return_value = mock_response

        intimations = await api_client.get_intimations_by_court("TJRO")

        assert isinstance(intimations, list)
        assert len(intimations) == 1
        assert intimations[0].id == 123
        assert intimations[0].sigla_tribunal == "TJRO"
