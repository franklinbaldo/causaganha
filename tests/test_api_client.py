from datetime import date
from unittest.mock import MagicMock, patch

import httpx
import pytest

from causaganha.api.client import PJeAPIClient
from tests.conftest import create_mock_intimation_item


@pytest.mark.asyncio
async def test_client_initializes_with_defaults():
    """Test client initialization"""
    client = PJeAPIClient()
    assert client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert client.client is not None
    await client.close()


@pytest.mark.asyncio
async def test_fetch_intimations_sends_correct_spec_params(api_client):
    """Test that query parameters sent match the OpenAPI spec."""
    mock_response = {
        "status": "success",
        "count": 1,
        "items": [create_mock_intimation_item(123456)],
    }

    with patch.object(api_client.client, "get") as mock_get:
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None
        mock_get.return_value = mock_response_obj

        intimations = await api_client.get_intimations_by_court(
            sigla_tribunal="TJRO",
            data_disponibilizacao_inicio=date(2024, 12, 1),
            data_disponibilizacao_fim=date(2024, 12, 2),
            pagina=1,
            itens_por_pagina=50,
        )

        assert len(intimations) == 1
        assert intimations[0].id == 123456

        args, kwargs = mock_get.call_args
        params = kwargs["params"]
        assert params["siglaTribunal"] == "TJRO"
        assert params["dataDisponibilizacaoInicio"] == "2024-12-01"
        assert params["dataDisponibilizacaoFim"] == "2024-12-02"
        assert params["pagina"] == 1
        assert params["itensPorPagina"] == 50


@pytest.mark.asyncio
async def test_fetch_handles_pagination_with_spec_params(api_client):
    """Test pagination works using spec-compliant parameters."""
    mock_response_p1 = {"status": "success", "count": 2, "items": [create_mock_intimation_item(1)]}
    mock_response_p2 = {"status": "success", "count": 2, "items": [create_mock_intimation_item(2)]}
    mock_response_p3 = {"status": "success", "count": 2, "items": []}

    with patch.object(api_client.client, "get") as mock_get:
        mock_resp1 = MagicMock()
        mock_resp1.json.return_value = mock_response_p1
        mock_resp1.raise_for_status.return_value = None

        mock_resp2 = MagicMock()
        mock_resp2.json.return_value = mock_response_p2
        mock_resp2.raise_for_status.return_value = None

        mock_resp3 = MagicMock()
        mock_resp3.json.return_value = mock_response_p3
        mock_resp3.raise_for_status.return_value = None

        mock_get.side_effect = [mock_resp1, mock_resp2, mock_resp3]

        intimations = await api_client.get_intimations_by_court(
            sigla_tribunal="TJRO", itens_por_pagina=1,
        )

        assert len(intimations) == 2
        assert intimations[0].id == 1
        assert intimations[1].id == 2
        assert mock_get.call_count == 3
        assert mock_get.call_args_list[0].kwargs["params"]["pagina"] == 1
        assert mock_get.call_args_list[1].kwargs["params"]["pagina"] == 2
        assert mock_get.call_args_list[2].kwargs["params"]["pagina"] == 3


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
            },
        ],
    }

    with patch.object(api_client.client, "get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        with pytest.raises(Exception):  # Pydantic ValidationError or similar
            await api_client.get_intimations_by_court("TJRO")
