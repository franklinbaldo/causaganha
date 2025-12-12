from datetime import date
from unittest.mock import MagicMock, patch

import httpx
import pytest

from causaganha_v2.api.client import PJeAPIClient
from causaganha_v2.api.models import Intimation


@pytest.mark.asyncio
async def test_client_initializes_with_defaults():
    """Test client initialization"""
    client = PJeAPIClient()

    assert client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert client.client is not None

    await client.close()


@pytest.mark.asyncio
async def test_fetch_intimations_success(api_client):
    """
    Test API fetch with mocked HTTP response
    """
    mock_response = {
        "status": "success",
        "count": 1,
        "items": [
            {
                "id": 123456,
                "numero_processo": "0001234-56.2024.8.22.0001",
                "data_disponibilizacao": "2024-12-01",
                "siglaTribunal": "TJRO",
                "tipoComunicacao": "INTIMACAO",
                "nomeOrgao": "Vara Civel",
                "texto": "Decisao...",
                "link": "https://pje.tjro.jus.br/doc/12345.pdf",
                "tipoDocumento": "Despacho",
                "nomeClasse": "Procedimento Comum",
                "hash": "abc123hash",
                "status": "A",
                "destinatarioadvogados": [],
            }
        ],
    }

    with patch.object(api_client.client, "get") as mock_get:
        # Create a sync mock for the response object
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None

        # AsyncMock returns this object when awaited
        mock_get.return_value = mock_response_obj

        intimations = await api_client.get_intimations_by_court(
            sigla_tribunal="TJRO", data_inicio=date(2024, 12, 1)
        )

        assert len(intimations) == 1
        assert isinstance(intimations[0], Intimation)
        assert intimations[0].id == 123456

        # Verify query params
        args, kwargs = mock_get.call_args
        assert "params" in kwargs
        assert kwargs["params"]["siglaTribunal"] == "TJRO"
        assert kwargs["params"]["dataInicio"] == "2024-12-01"


@pytest.mark.asyncio
async def test_fetch_handles_pagination(api_client):
    """Test pagination works"""
    # Page 1
    mock_response_p1 = {
        "status": "success",
        "count": 2,  # Total 2
        "items": [
            {
                "id": 1,
                "numero_processo": "proc1",
                "siglaTribunal": "TJRO",
                "data_disponibilizacao": "2024-01-01",
                "tipoComunicacao": "X",
                "nomeOrgao": "X",
                "texto": "X",
                "link": "X",
                "tipoDocumento": "X",
                "nomeClasse": "X",
                "hash": "X",
                "status": "X",
            }
        ],
    }
    # Page 2
    mock_response_p2 = {
        "status": "success",
        "count": 2,
        "items": [
            {
                "id": 2,
                "numero_processo": "proc2",
                "siglaTribunal": "TJRO",
                "data_disponibilizacao": "2024-01-01",
                "tipoComunicacao": "X",
                "nomeOrgao": "X",
                "texto": "X",
                "link": "X",
                "tipoDocumento": "X",
                "nomeClasse": "X",
                "hash": "X",
                "status": "X",
            }
        ],
    }

    with patch.object(api_client.client, "get") as mock_get:
        # Mock side effects for pagination
        mock_resp_obj1 = MagicMock()
        mock_resp_obj1.json.return_value = mock_response_p1
        mock_resp_obj1.raise_for_status.return_value = None

        mock_resp_obj2 = MagicMock()
        mock_resp_obj2.json.return_value = mock_response_p2
        mock_resp_obj2.raise_for_status.return_value = None

        mock_get.side_effect = [mock_resp_obj1, mock_resp_obj2]

        intimations = await api_client.get_intimations_by_court(
            sigla_tribunal="TJRO", limit_per_page=1
        )

        assert len(intimations) == 2
        assert intimations[0].id == 1
        assert intimations[1].id == 2

        assert mock_get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_raises_on_http_error(api_client):
    """Test error handling"""
    with patch.object(api_client.client, "get") as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network error")

        with pytest.raises(httpx.HTTPError):
            await api_client.get_intimations_by_court("TJRO")


@pytest.mark.asyncio
async def test_fetch_raises_validation_error(api_client):
    """Test validation error handling"""
    mock_response = {
        "status": "success",
        "count": 1,
        "items": [
            {
                "id": "bad_id",  # Should be int
                "numero_processo": "proc1",
                "siglaTribunal": "TJRO",
                # Missing required fields
            }
        ],
    }

    with patch.object(api_client.client, "get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        with pytest.raises(Exception):  # Pydantic ValidationError or similar
            await api_client.get_intimations_by_court("TJRO")
