"""Unit tests for collection pipeline."""

import io
import json
import zipfile
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from causaganha.pipeline.collect import collect_metadata_for_court


@pytest.fixture
def mock_connection():
    """Mock database connection."""
    with patch("causaganha.storage.connection.get_connection") as mock:
        yield mock


@pytest.fixture
def mock_store_intimations():
    """Mock store_intimations."""
    with patch("causaganha.pipeline.collect.store_intimations") as mock:
        mock.return_value = 1  # 1 new record
        yield mock


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client."""
    with patch("httpx.AsyncClient") as mock:
        client = AsyncMock()
        mock.return_value.__aenter__.return_value = client
        yield client


def create_mock_zip_content(items):
    """Create a valid ZIP file content with JSON items."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("data.json", json.dumps({"items": items}))
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_collect_metadata_success(mock_connection, mock_store_intimations, mock_httpx_client):
    """Test successful collection flow."""
    # Setup
    tribunal = "TJRO"
    today = date.today().isoformat()

    # Mock responses
    # 1. Info request
    info_resp = MagicMock()
    info_resp.status_code = 200
    info_resp.json.return_value = {"url": "http://example.com/data.zip"}

    # 2. ZIP request
    item = {
        "id": 123,
        "numeroProcesso": "0001234-56.2024.8.22.0001",
        "dataDisponibilizacao": "2024-12-01",
        "siglaTribunal": "TJRO",
        "tipoComunicacao": "Intimação",
        "nomeOrgao": "Vara Cível",
        "texto": "Decisão...",
        "link": "https://example.com/doc.pdf",
        "tipoDocumento": "Decisão",
        "nomeClasse": "Procedimento Comum",
        "codigoClasse": 123,
        "hash": "abc123hash",
        "status": "D",
    }
    zip_content = create_mock_zip_content([item])

    zip_resp = MagicMock()
    zip_resp.status_code = 200
    zip_resp.content = zip_content

    mock_httpx_client.get.side_effect = [info_resp, zip_resp]

    # Execute
    result = await collect_metadata_for_court(tribunal, days_back=1)

    # Verify
    assert result["status"] == "success"
    assert result["total_collected"] == 1
    assert len(result["details"]) == 1

    # Verify store_intimations was called
    mock_store_intimations.assert_called_once()
    call_args = mock_store_intimations.call_args
    # First arg is connection, second is list of objects
    assert call_args[0][0] == mock_connection()
    intimations = call_args[0][1]
    assert len(intimations) == 1
    assert intimations[0].id == 123
    assert intimations[0].sigla_tribunal == "TJRO"


@pytest.mark.asyncio
async def test_collect_metadata_no_download_url(
    mock_connection, mock_store_intimations, mock_httpx_client
):
    """Test when no download URL is available."""
    # Mock info response with no URL
    info_resp = MagicMock()
    info_resp.status_code = 200
    info_resp.json.return_value = {"url": None}

    mock_httpx_client.get.return_value = info_resp

    result = await collect_metadata_for_court("TJRO", days_back=1)

    assert result["status"] == "success"
    assert result["total_collected"] == 0
    mock_store_intimations.assert_not_called()
