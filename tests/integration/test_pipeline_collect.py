from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from causaganha.api.models import Intimation
from causaganha.pipeline.collect import run_collection


@pytest.mark.asyncio
async def test_run_collection_success(tmp_path: Path) -> None:
    from causaganha.storage.connection import get_connection
    from causaganha.storage.schema import create_schema

    db_path = tmp_path / "test.duckdb"
    con = get_connection(str(db_path))
    create_schema(con)

    # Mock API Client
    mock_api_client = AsyncMock()

    # Create sample data
    intimations = [
        Intimation(
            id=1,
            numero_processo="1234567-89.2024.8.00.0000",
            data_disponibilizacao="2024-01-01",
            siglaTribunal="TJRO",
            tipoComunicacao="INTIMAÇÃO",
            nomeOrgao="Vara Cível",
            texto="Decisão favorável.",
            link="http://example.com/decision.pdf",
            tipoDocumento="Decisão",
            nomeClasse="Procedimento Comum",
            hash="abc123hash",
            status="ATIVO",
        ),
    ]

    mock_api_client.get_intimations_by_court.return_value = intimations

    # Patch the class PJeAPIClient so that run_collection uses our mock
    # Note: run_collection instantiates PJeAPIClient()

    with patch("causaganha.pipeline.collect.PJeAPIClient", return_value=mock_api_client):
         await run_collection(db_path=str(db_path), start_date="2024-01-01", end_date="2024-01-02", courts=["TJRO"])

    # Verify data is stored
    t = con.table("intimations")
    rows = t.execute()
    assert len(rows) == 1
    assert rows.iloc[0]["numero_processo"] == "1234567-89.2024.8.00.0000"

    # Verify API was called correctly
    mock_api_client.get_intimations_by_court.assert_called_once()
    mock_api_client.close.assert_called_once()
