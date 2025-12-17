"""
Unit tests for PJe API Client
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from causaganha.api.client import PJeAPIClient

@pytest.mark.asyncio
async def test_client_initialization() -> None:
    """Test that client initializes with correct defaults"""
    client = PJeAPIClient()

    assert client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert client.client is not None
    assert isinstance(client.client, httpx.AsyncClient)

    await client.close()

@pytest.mark.asyncio
async def test_fetch_intimations_returns_list(api_client: PJeAPIClient) -> None:
    """Test that fetching returns a list of intimations"""

    mock_response = {
        "status": "success",
        "count": 0,
        "items": []
    }

    # Mock the request
    with patch.object(api_client.client, 'request', new_callable=AsyncMock) as mock_request:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None
        mock_request.return_value = mock_resp

        intimations = await api_client.get_intimations_by_court("TJRO")

        assert isinstance(intimations, list)
        assert len(intimations) == 0

@pytest.mark.asyncio
async def test_fetch_intimations_success(api_client: PJeAPIClient) -> None:
    """Test API fetch with mocked HTTP response"""
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
                "hash": "abc123",
                "status": "P",
                "destinatarioadvogados": [],
                "destinatarios": []
            }
        ]
    }

    with patch.object(api_client.client, 'request', new_callable=AsyncMock) as mock_request:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None
        mock_request.return_value = mock_resp

        intimations = await api_client.get_intimations_by_court("TJRO")

        assert len(intimations) == 1
        assert intimations[0].id == 123456
        # Pydantic model uses camelCase for alias but Python attribute is snake_case or same name?
        # The Intimation model uses alias 'siglaTribunal'.
        # By default pydantic access by attribute name.
        # Let's check the schema definition if I can access it.
        # The error says "AttributeError: 'Intimation' object has no attribute 'siglaTribunal'".
        # If I look at the implementation plan, the model is defined as:
        # class Intimation(BaseModel):
        #    ...
        #    siglaTribunal: str = Field(alias='siglaTribunal')
        #
        # BUT, usually Pydantic fields are snake_case in python and aliased to camelCase for JSON.
        # If the python field name IS siglaTribunal, then it should work.
        # However, looking at the error `Did you mean: 'sigla_tribunal'?` suggests that
        # maybe the implementation (which I haven't written yet but is partially there?) uses snake_case.
        # Wait, I am writing tests BEFORE implementation. The implementation I see in `src/causaganha/api/client.py` exists?
        # I should check `src/causaganha/api/client.py`.

        # If I am following TDD, I should fix the test or the implementation.
        # Since the error `Did you mean: 'sigla_tribunal'?` appeared, it means the model likely has `sigla_tribunal`.
        # I will check the file content first.
        assert intimations[0].sigla_tribunal == "TJRO"

@pytest.mark.asyncio
async def test_fetch_intimations_pagination(api_client: PJeAPIClient) -> None:
    """Test pagination"""

    # Page 1
    page1_response = {
        "status": "success",
        "count": 2,
        "items": [
            {
                "id": 1,
                "numero_processo": "proc1",
                "data_disponibilizacao": "2024-12-01",
                "siglaTribunal": "TJRO",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara 1",
                "texto": "Txt",
                "link": "link1",
                "tipoDocumento": "Doc",
                "nomeClasse": "Class",
                "hash": "h1",
                "status": "P"
            }
        ]
    }

    # Page 2
    page2_response = {
        "status": "success",
        "count": 2,
        "items": [
            {
                "id": 2,
                "numero_processo": "proc2",
                "data_disponibilizacao": "2024-12-01",
                "siglaTribunal": "TJRO",
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara 1",
                "texto": "Txt",
                "link": "link2",
                "tipoDocumento": "Doc",
                "nomeClasse": "Class",
                "hash": "h2",
                "status": "P"
            }
        ]
    }

    with patch.object(api_client.client, 'request', new_callable=AsyncMock) as mock_request:
        mock_resp1 = MagicMock()
        mock_resp1.json.return_value = page1_response
        mock_resp1.raise_for_status.return_value = None

        mock_resp2 = MagicMock()
        mock_resp2.json.return_value = page2_response
        mock_resp2.raise_for_status.return_value = None

        # Simulate returning page 1 then page 2
        # Note: In implementation we need to handle pagination logic.
        # The client will call request multiple times.
        mock_request.side_effect = [mock_resp1, mock_resp2]

        # We set limit_per_page to 1 to force pagination
        intimations = await api_client.get_intimations_by_court("TJRO", limit_per_page=1)

        assert len(intimations) == 2
        assert intimations[0].id == 1
        assert intimations[1].id == 2
        assert mock_request.call_count == 2

@pytest.mark.asyncio
async def test_fetch_raises_on_http_error(api_client: PJeAPIClient) -> None:
    """Test error handling"""

    with patch.object(api_client.client, 'request', new_callable=AsyncMock) as mock_request:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPError("Network error")
        mock_request.return_value = mock_resp

        with pytest.raises(httpx.HTTPError):
            await api_client.get_intimations_by_court("TJRO")
