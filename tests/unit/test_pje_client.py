"""Unit tests for PJe API Client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from causaganha.clients.pje import PJeAPIClient


INTIMATION_ID = 123456

@pytest.mark.asyncio
async def test_client_initializes_with_defaults() -> None:
    """Test that client initializes with correct defaults."""
    client = PJeAPIClient()
    assert client.base_url == "https://comunicaapi.pje.jus.br/api/v1"
    assert client.client is not None
    await client.close()

@pytest.mark.asyncio
async def test_fetch_intimations_parses_response() -> None:
    """Test that fetching correctly parses the API response."""
    client = PJeAPIClient()

    # Mock the API response with sample data
    mock_data = {
        "status": "success",
        "count": 1,
        "items": [
            {
                "id": INTIMATION_ID,
                "numero_processo": "0001234-56.2024.8.22.0001",
                "numeroprocessocommascara": "0001234-56.2024.8.22.0001",
                "data_disponibilizacao": "2024-12-01",
                "siglaTribunal": "TJRO",
                "idOrgao": 928,
                "tipoComunicacao": "Intimação",
                "nomeOrgao": "Vara Cível",
                "texto": "Teor do ato",
                "link": "https://example.com/doc.pdf",
                "tipoDocumento": "Despacho",
                "nomeClasse": "Procedimento Comum",
                "codigoClasse": "7",
                "hash": "abc123hash",
                "status": "P",
                "destinatarioadvogados": [
                    {
                        "advogado": {
                            "id": 1,
                            "nome": "ADVOGADO TESTE",
                            "numero_oab": "12345",
                            "uf_oab": "RO",
                        },
                    },
                ],
                "destinatarios": [
                    {
                        "nome": "PARTE TESTE",
                        "polo": "A",
                    },
                ],
            },
        ],
    }

    with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        intimations = await client.get_intimations_by_court("TJRO")

        assert len(intimations) == 1
        intimation = intimations[0]

        # Verify field mapping (snake_case vs alias)
        assert intimation.id == INTIMATION_ID
        assert intimation.sigla_tribunal == "TJRO"
        assert intimation.tipo_comunicacao == "Intimação"
        assert intimation.destinatarioadvogados[0].advogado.nome == "ADVOGADO TESTE"
        assert intimation.destinatarioadvogados[0].advogado.numero_oab == "12345"

    await client.close()
