from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from causaganha.analysis.models import DecisionAnalysis, Outcome
from causaganha.domain.models import Intimation
from causaganha.pipeline.analyze import run_analysis
from causaganha.storage.repository import IntimationRepository


@pytest.mark.asyncio
async def test_run_analysis_success(tmp_path: Path) -> None:
    from causaganha.storage.connection import get_connection
    from causaganha.storage.schema import create_schema

    db_path = tmp_path / "test.duckdb"
    con = get_connection(str(db_path))
    create_schema(con)
    repository = IntimationRepository(con)

    # 1. Seed DB with unanalyzed intimation
    # Correctly using Domain Model for seeding via Repository
    intimation = Intimation(
        id=100,
        numero_processo="1234567-89.2024.8.00.0000",
        data_disponibilizacao=date(2024, 1, 1),
        sigla_tribunal="TJRO",
        tipo_comunicacao="INTIMAÇÃO",
        nome_orgao="Vara Cível",
        texto="Decisão.",
        link="http://example.com/decision.pdf",
        tipo_documento="Decisão",
        nome_classe="Procedimento Comum",
        hash="abc123hash",
        status="ATIVO",
        advogados=[],
        partes=[]
    )
    await repository.store_intimations([intimation])

    # 2. Mock DocumentService
    mock_doc_service = AsyncMock()
    mock_doc_service.download_pdf.return_value = b"%PDF-1.5 fake content"

    # 3. Mock Analyzer
    mock_analysis = DecisionAnalysis(
        outcome=Outcome.WIN,
        summary="Won",
        judge_name="Judge",
        confidence_score=0.9,
    )
    mock_analyzer = AsyncMock()
    mock_analyzer.analyze_decision.return_value = mock_analysis

    # Run
    await run_analysis(
        repository=repository,
        doc_service=mock_doc_service,
        analyzer=mock_analyzer,
        limit=1
    )

    # Verify
    mock_doc_service.download_pdf.assert_called_with("http://example.com/decision.pdf")
    mock_analyzer.analyze_decision.assert_called_once()

    # Check DB
    t = con.table("analysis_results")
    rows = t.execute()
    assert len(rows) == 1
    assert rows.iloc[0]["intimation_id"] == 100
    assert rows.iloc[0]["outcome"] == "WIN"
