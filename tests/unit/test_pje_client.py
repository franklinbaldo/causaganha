"""Unit tests for PJe API client."""

from datetime import date
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
async def test_client_initialization():
    """Test that client initializes with correct defaults."""
    client = PJeAPIClient()

    assert client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert client.client is not None

    await client.close()


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
                "siglaTribunal": "TJRO",
                "data_disponibilizacao": "2024-12-01",
                "link": "https://example.com/doc.pdf",
                "hash": "abc123",
                "status": "P",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara Cível",
                "texto": "Intimação de teste",
                "tipoDocumento": "Despacho",
                "nomeClasse": "Procedimento Comum",
                "codigoClasse": "7",
                "destinatarioadvogados": [],
                "destinatarios": [],
            }
        ],
    }

    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        intimations = await api_client.get_intimations_by_court("TJRO")

        assert len(intimations) == 1
        assert isinstance(intimations[0], Intimation)
        assert intimations[0].id == 123
        assert intimations[0].sigla_tribunal == "TJRO"


@pytest.mark.asyncio
async def test_fetch_intimations_with_nested_objects(api_client):
    """Test API fetch with populated nested objects (lawyers and parties)."""
    mock_response = {
        "status": "success",
        "count": 1,
        "items": [
            {
                "id": 456,
                "numero_processo": "0001234-56.2024.8.22.0001",
                "siglaTribunal": "TJRO",
                "data_disponibilizacao": "2024-12-01",
                "link": "link",
                "hash": "hash",
                "status": "P",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara",
                "texto": "Texto",
                "tipoDocumento": "Doc",
                "nomeClasse": "Classe",
                "codigoClasse": "1",
                "destinatarioadvogados": [
                    {
                        "advogado": {
                            "id": 1001,
                            "nome": "Dr. Strange",
                            "numero_oab": "12345",
                            "uf_oab": "NY",
                        }
                    }
                ],
                "destinatarios": [{"nome": "Tony Stark", "polo": "A"}],
            }
        ],
    }

    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        intimations = await api_client.get_intimations_by_court("TJRO")

        assert len(intimations) == 1
        intimation = intimations[0]
        assert len(intimation.destinatarioadvogados) == 1
        assert intimation.destinatarioadvogados[0].advogado.nome == "Dr. Strange"
        assert intimation.destinatarioadvogados[0].advogado.numero_oab == "12345"
        assert len(intimation.destinatarios) == 1
        assert intimation.destinatarios[0].nome == "Tony Stark"
        assert intimation.destinatarios[0].polo == "A"


@pytest.mark.asyncio
async def test_fetch_intimations_http_error(api_client):
    """Test error handling with mocked HTTP error."""
    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("Network error")

        with pytest.raises(httpx.HTTPError):
            await api_client.get_intimations_by_court("TJRO")


@pytest.mark.asyncio
async def test_fetch_handles_pagination(api_client):
    """Test pagination logic."""
    # Page 1: 1 item, total count 2
    page1_response = {
        "status": "success",
        "count": 2,
        "items": [
            {
                "id": 1,
                "numero_processo": "proc1",
                "siglaTribunal": "TJRO",
                "data_disponibilizacao": "2024-12-01",
                "link": "link1",
                "hash": "hash1",
                "status": "P",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara 1",
                "texto": "txt1",
                "tipoDocumento": "doc1",
                "nomeClasse": "cls1",
                "codigoClasse": "1",
            }
        ],
    }
    # Page 2: 1 item
    page2_response = {
        "status": "success",
        "count": 2,
        "items": [
            {
                "id": 2,
                "numero_processo": "proc2",
                "siglaTribunal": "TJRO",
                "data_disponibilizacao": "2024-12-01",
                "link": "link2",
                "hash": "hash2",
                "status": "P",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara 1",
                "texto": "txt2",
                "tipoDocumento": "doc2",
                "nomeClasse": "cls1",
                "codigoClasse": "1",
            }
        ],
    }

    with patch.object(api_client.client, "get", new_callable=AsyncMock) as mock_get:
        # Return page 1 then page 2
        resp1 = MagicMock()
        resp1.json.return_value = page1_response
        resp1.raise_for_status.return_value = None

        resp2 = MagicMock()
        resp2.json.return_value = page2_response
        resp2.raise_for_status.return_value = None

        mock_get.side_effect = [resp1, resp2]

        # Call with smaller page limit to force pagination
        intimations = await api_client.get_intimations_by_court(
            "TJRO", limit_per_page=1
        )

        assert len(intimations) == 2
        assert intimations[0].id == 1
        assert intimations[1].id == 2
        assert mock_get.call_count == 2
