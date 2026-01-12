from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from causaganha.domain.models import Intimation
from causaganha.application.pipeline.collect import run_collection
from causaganha.infrastructure.storage.connection import get_connection
from causaganha.infrastructure.storage.repositories.intimation import IntimationRepository
from causaganha.infrastructure.storage.schema import create_schema


@pytest.mark.asyncio
async def test_run_collection_success(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    con = get_connection(str(db_path))
    create_schema(con)
    repository = IntimationRepository(con)

    # Mock API Client
    mock_api_client = AsyncMock()

    # Create sample data using Domain Model
    intimations = [
        Intimation(
            id=1,
            numero_processo="1234567-89.2024.8.00.0000",
            data_disponibilizacao=date(2024, 1, 1),
            sigla_tribunal="TJRO",
            tipo_comunicacao="INTIMAÇÃO",
            nome_orgao="Vara Cível",
            texto="Decisão favorável.",
            link="http://example.com/decision.pdf",
            tipo_documento="Decisão",
            nome_classe="Procedimento Comum",
            hash="abc123hash",
            status="ATIVO",
            advogados=[],
            partes=[],
        ),
    ]

    mock_api_client.get_intimations_by_court.return_value = intimations

    # Pass dependencies explicitly
    await run_collection(
        repository=repository,
        client=mock_api_client,
        start_date="2024-01-01",
        end_date="2024-01-02",
        courts=["TJRO"],
    )

    # Verify data is stored
    t = con.table("intimations")
    rows = t.execute()
    assert len(rows) == 1
    assert rows.iloc[0]["numero_processo"] == "1234567-89.2024.8.00.0000"

    # Verify API was called correctly
    mock_api_client.get_intimations_by_court.assert_called_once()

    # Verify arguments - this catches interface mismatches
    call_kwargs = mock_api_client.get_intimations_by_court.call_args.kwargs
    assert call_kwargs["sigla_tribunal"] == "TJRO"
    # Ensure usage matches api definition (data_disponibilizacao_inicio)
    assert "data_disponibilizacao_inicio" in call_kwargs
    assert call_kwargs["data_disponibilizacao_inicio"] == date(2024, 1, 1)
    assert "data_disponibilizacao_fim" in call_kwargs
    assert call_kwargs["data_disponibilizacao_fim"] == date(2024, 1, 2)

    # Note: run_collection no longer closes the client, the caller does.
    # So we don't assert close called here unless we mock the context manager if used.
