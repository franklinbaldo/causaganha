import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from causaganha.v2.api.client import PJeAPIClient

@pytest.fixture
async def api_client():
    client = PJeAPIClient()
    yield client
    await client.close()

@pytest.mark.asyncio
async def test_client_initialization(api_client):
    assert api_client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert api_client.client is not None
    assert isinstance(api_client.client, httpx.AsyncClient)

@pytest.mark.asyncio
async def test_get_intimations_by_court_success(api_client):
    mock_response = {
        "items": [
            {
                "id": 123456,
                "numero_processo": "0001234-56.2024.8.22.0001",
                "numeroprocessocommascara": "0001234-56.2024.8.22.0001",
                "data_disponibilizacao": "2024-01-01",
                "siglaTribunal": "TJRO",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara Cível",
                "texto": "Decisão...",
                "link": "http://example.com/pdf",
                "tipoDocumento": "Despacho",
                "nomeClasse": "Procedimento Comum",
                "hash": "abc123hash",
                "status": "D",
                "destinatarioadvogados": [],
                "destinatarios": []
            }
        ],
        "count": 1
    }

    with patch.object(api_client.client, 'get') as mock_get:
        mock_get.return_value = MagicMock()
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.raise_for_status = lambda: None

        intimations = await api_client.get_intimations_by_court("TJRO")

        assert len(intimations) == 1
        assert intimations[0].id == 123456
        assert intimations[0].sigla_tribunal == "TJRO"

@pytest.mark.asyncio
async def test_get_intimations_pagination(api_client):
    # Page 1
    response1 = {
        "items": [{"id": 1, "numero_processo": "1", "data_disponibilizacao": "2024", "siglaTribunal": "TJRO", "tipoComunicacao": "T", "nomeOrgao": "O", "texto": "T", "link": "L", "tipoDocumento": "D", "nomeClasse": "C", "hash": "H", "status": "S"}],
        "count": 2
    }
    # Page 2
    response2 = {
        "items": [{"id": 2, "numero_processo": "2", "data_disponibilizacao": "2024", "siglaTribunal": "TJRO", "tipoComunicacao": "T", "nomeOrgao": "O", "texto": "T", "link": "L", "tipoDocumento": "D", "nomeClasse": "C", "hash": "H", "status": "S"}],
        "count": 2
    }

    with patch.object(api_client.client, 'get') as mock_get:
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: response1),
            MagicMock(status_code=200, json=lambda: response2)
        ]

        intimations = await api_client.get_intimations_by_court("TJRO", limit_per_page=1)

        assert len(intimations) == 2
        assert intimations[0].id == 1
        assert intimations[1].id == 2
        assert mock_get.call_count == 2

@pytest.mark.asyncio
async def test_api_error_handling(api_client):
    with patch.object(api_client.client, 'get') as mock_get:
        mock_get.side_effect = httpx.HTTPError("API Error")

        with pytest.raises(httpx.HTTPError):
            await api_client.get_intimations_by_court("TJRO")
