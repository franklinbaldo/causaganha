"""Unit tests for PJe API Client (v2)."""

from datetime import date
from unittest.mock import MagicMock, patch

import httpx
import pytest

from causaganha.v2.api.client import PJeAPIClient
from causaganha.v2.api.models import Intimation


@pytest.mark.asyncio
async def test_client_initialization_defaults() -> None:
    """Test that client initializes with correct default values."""
    client = PJeAPIClient()

    assert client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert isinstance(client.client, httpx.AsyncClient)

    await client.close()


@pytest.mark.asyncio
async def test_client_initialization_custom() -> None:
    """Test that client initializes with custom values."""
    custom_url = "https://custom.api/v1"
    client = PJeAPIClient(base_url=custom_url, timeout=60)

    assert client.base_url == custom_url
    assert client.client.timeout.read == 60

    await client.close()


@pytest.mark.asyncio
async def test_get_intimations_by_court_success() -> None:
    """Test fetching intimations successfully."""
    client = PJeAPIClient()

    mock_response = {
        "status": "success",
        "count": 1,
        "items": [
            {
                "id": 123456,
                "data_disponibilizacao": "2024-12-01",
                "siglaTribunal": "TJRO",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara Cível",
                "numero_processo": "00012345620248220001",
                "numeroprocessocommascara": "0001234-56.2024.8.22.0001",
                "nomeClasse": "Procedimento Comum",
                "codigoClasse": "7",
                "texto": "Decisão...",
                "link": "https://example.com/doc.pdf",
                "hash": "abc123hash",
                "status": "D",
                "tipoDocumento": "Decisão",
                "destinatarioadvogados": [],
                "destinatarios": [],
            },
        ],
    }

    with patch.object(client.client, "get") as mock_get:
        # Configure mock to be awaitable and return response object
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        mock_get.return_value = mock_response_obj

        results = await client.get_intimations_by_court(
            sigla_tribunal="TJRO",
            data_inicio=date(2024, 12, 1),
        )

        assert len(results) == 1
        assert isinstance(results[0], Intimation)
        assert results[0].id == 123456
        assert results[0].siglaTribunal == "TJRO"

        # Verify call args
        mock_get.assert_called()
        _args, kwargs = mock_get.call_args
        assert kwargs["params"]["siglaTribunal"] == "TJRO"
        assert kwargs["params"]["dataInicio"] == "2024-12-01"

    await client.close()


@pytest.mark.asyncio
async def test_get_intimations_pagination() -> None:
    """Test automatic pagination."""
    client = PJeAPIClient()

    # Mock multiple pages
    page1 = {
        "status": "success",
        "count": 2,
        "items": [
            {
                "id": 1,
                "siglaTribunal": "TJRO",
                "numero_processo": "1",
                "data_disponibilizacao": "2024-01-01",
                "tipoComunicacao": "T",
                "nomeOrgao": "O",
                "texto": "T",
                "link": "L",
                "tipoDocumento": "D",
                "nomeClasse": "C",
                "hash": "H",
                "status": "S",
            }
        ],
    }
    page2 = {
        "status": "success",
        "count": 2,
        "items": [
            {
                "id": 2,
                "siglaTribunal": "TJRO",
                "numero_processo": "2",
                "data_disponibilizacao": "2024-01-01",
                "tipoComunicacao": "T",
                "nomeOrgao": "O",
                "texto": "T",
                "link": "L",
                "tipoDocumento": "D",
                "nomeClasse": "C",
                "hash": "H",
                "status": "S",
            }
        ],
    }

    with patch.object(client.client, "get") as mock_get:
        # Create response objects
        resp1 = MagicMock()
        resp1.json.return_value = page1
        resp1.raise_for_status.return_value = None

        resp2 = MagicMock()
        resp2.json.return_value = page2
        resp2.raise_for_status.return_value = None

        resp3 = MagicMock()
        resp3.json.return_value = {"items": []}
        resp3.raise_for_status.return_value = None

        mock_get.side_effect = [resp1, resp2, resp3]

        results = await client.get_intimations_by_court(
            sigla_tribunal="TJRO",
            limit_per_page=1,
        )

        assert len(results) == 2
        assert results[0].id == 1
        assert results[1].id == 2

        # It stops when total_count is reached, so it should call exactly 2 times
        # because after page 2, len(all_intimations) (2) >= total_count (2)
        assert mock_get.call_count == 2

    await client.close()
