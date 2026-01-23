"""TDD Example: Building the PJe API Client.

Each test is written before the implementation.
"""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from causaganha.api.client import PJeAPIClient


# TEST 1: Client initialization
@pytest.mark.asyncio
async def test_client_initializes_with_defaults() -> None:
    """RED -> GREEN -> REFACTOR.

    This test is written FIRST, before PJeAPIClient exists.
    """
    client = PJeAPIClient()

    assert client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert client.client is not None

    await client.close()


# TEST 2: Fetching returns list
@pytest.mark.asyncio
async def test_fetch_intimations_returns_list() -> None:
    """Next test: Method should return a list.

    Write this BEFORE implementing get_intimations_by_court.
    """
    client = PJeAPIClient()

    mock_response = Mock()
    mock_response.json.return_value = {"items": [], "count": 0}
    mock_response.raise_for_status = lambda: None

    with patch.object(client.client, "get", new_callable=Mock) as mock_get:
        # We need to make the return value awaitable since client.get is async
        async def async_return() -> Mock:
            return mock_response

        mock_get.return_value = async_return()

        intimations = await client.get_intimations_by_court("TJRO")

        assert isinstance(intimations, list)

    await client.close()


# TEST 3: Pagination works
@pytest.mark.asyncio
async def test_fetch_handles_pagination() -> None:
    """Test pagination BEFORE implementing it."""
    client = PJeAPIClient()

    # Mock API to return multiple pages
    mock_page1 = {
        "status": "success",
        "count": 101,
        "items": [
            {
                "id": i,
                "siglaTribunal": "TJRO",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara",
                "texto": "test",
                "link": "http://test",
                "tipoDocumento": "Despacho",
                "nomeClasse": "Classe",
                "hash": "hash",
                "status": "P",
                "numero_processo": f"proc{i}",
                "data_disponibilizacao": "2023-01-01",
            }
            for i in range(100)
        ],
    }
    mock_page2 = {
        "status": "success",
        "count": 101,
        "items": [
            {
                "id": 100,
                "siglaTribunal": "TJRO",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara",
                "texto": "test",
                "link": "http://test",
                "tipoDocumento": "Despacho",
                "nomeClasse": "Classe",
                "hash": "hash",
                "status": "P",
                "numero_processo": "proc100",
                "data_disponibilizacao": "2023-01-01",
            },
        ],
    }

    # Create mock response objects
    # Note: json() on Response is synchronous
    mock_response1 = Mock()
    mock_response1.json.return_value = mock_page1
    mock_response1.raise_for_status = lambda: None

    mock_response2 = Mock()
    mock_response2.json.return_value = mock_page2
    mock_response2.raise_for_status = lambda: None

    # client.get is async, so side_effect should return awaitables (coroutines)
    async def side_effect(*_args: object, **kwargs: object) -> Mock:
        # We can check params here if we wanted to differentiate by offset
        params = kwargs.get("params", {})
        offset = 0
        if isinstance(params, dict):
            offset = params.get("offset", 0)

        if offset == 0:
            return mock_response1
        return mock_response2

    with patch.object(client.client, "get", side_effect=side_effect):
        intimations = await client.get_intimations_by_court("TJRO")

        # Should have fetched from multiple pages
        expected_count = 101
        assert len(intimations) == expected_count

    await client.close()


@pytest.mark.asyncio
async def test_fetch_uses_date_filters() -> None:
    """Test that date filters are passed to the API."""
    client = PJeAPIClient()
    start_date = date(2023, 1, 1)
    end_date = date(2023, 1, 31)

    mock_response = Mock()
    mock_response.json.return_value = {"items": [], "count": 0}
    mock_response.raise_for_status = lambda: None

    with patch.object(client.client, "get", new_callable=Mock) as mock_get:

        async def async_return() -> Mock:
            return mock_response

        mock_get.return_value = async_return()

        await client.get_intimations_by_court(
            "TJRO",
            data_inicio=start_date,
            data_fim=end_date,
        )

        # Verify arguments passed to get
        call_args = mock_get.call_args
        assert call_args is not None
        _, kwargs = call_args
        params = kwargs["params"]

        assert params["dataDisponibilizacaoInicio"] == "2023-01-01"
        assert params["dataDisponibilizacaoFim"] == "2023-01-31"

    await client.close()
