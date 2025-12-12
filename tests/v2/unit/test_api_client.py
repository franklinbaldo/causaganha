"""Unit tests for the PJe API Client."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from causaganha_v2.api.client import PJeAPIClient


@pytest.mark.asyncio
async def test_client_initialization() -> None:
    """Test that client initializes with correct defaults."""
    client = PJeAPIClient()

    assert client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert isinstance(client.client, httpx.AsyncClient)

    await client.close()


@pytest.mark.asyncio
async def test_fetch_intimations_pagination() -> None:
    """Test API fetch with pagination."""
    client = PJeAPIClient()

    # Mock response for page 1
    page1_response = {
        "status": "success",
        "count": 2,
        "items": [
            {
                "id": 1,
                "numero_processo": "proc1",
                "siglaTribunal": "TJRO",
                "data_disponibilizacao": "2024-01-01",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara Cível",
                "texto": "Decisão...",
                "link": "http://example.com/doc1.pdf",
                "tipoDocumento": "Despacho",
                "nomeClasse": "Procedimento Comum",
                "hash": "hash1",
                "status": "A",
            },
        ],
    }

    # Mock response for page 2
    page2_response = {
        "status": "success",
        "count": 2,
        "items": [
            {
                "id": 2,
                "numero_processo": "proc2",
                "siglaTribunal": "TJRO",
                "data_disponibilizacao": "2024-01-01",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara Cível",
                "texto": "Decisão...",
                "link": "http://example.com/doc2.pdf",
                "tipoDocumento": "Despacho",
                "nomeClasse": "Procedimento Comum",
                "hash": "hash2",
                "status": "A",
            },
        ],
    }

    # Mock response for page 3 (empty)
    page3_response = {
        "status": "success",
        "count": 2,
        "items": [],
    }

    with patch.object(client.client, "get") as mock_get:
        mock_get.side_effect = [
            AsyncMock(
                status_code=200,
                json=lambda: page1_response,
                raise_for_status=lambda: None,
            ),
            AsyncMock(
                status_code=200,
                json=lambda: page2_response,
                raise_for_status=lambda: None,
            ),
            AsyncMock(
                status_code=200,
                json=lambda: page3_response,
                raise_for_status=lambda: None,
            ),
        ]

        intimations = await client.get_intimations_by_court(
            "TJRO",
            limit_per_page=1,
        )

        assert len(intimations) == 2
        assert intimations[0].id == 1
        assert intimations[1].id == 2
        assert mock_get.call_count == 2  # Only 2 calls needed because count check stops it

    await client.close()


@pytest.mark.asyncio
async def test_fetch_intimations_error() -> None:
    """Test API fetch with error."""
    client = PJeAPIClient()

    with patch.object(client.client, "get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network error")

        with pytest.raises(httpx.HTTPError):
            await client.get_intimations_by_court("TJRO")

    await client.close()


@pytest.mark.asyncio
async def test_fetch_intimations_success() -> None:
    """Test API fetch with mocked HTTP response."""
    client = PJeAPIClient()

    mock_response = {
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
                "texto": "Decisão...",
                "link": "http://example.com/doc.pdf",
                "tipoDocumento": "Despacho",
                "nomeClasse": "Procedimento Comum",
                "hash": "abc123456",
                "status": "A",
            },
        ],
    }

    # Mock the HTTP call
    with patch.object(client.client, "get") as mock_get:
        mock_get.return_value = AsyncMock(spec=httpx.Response)
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.raise_for_status = lambda: None

        intimations = await client.get_intimations_by_court("TJRO")

        assert len(intimations) == 1
        assert intimations[0].id == 123
        assert intimations[0].siglaTribunal == "TJRO"

    await client.close()
