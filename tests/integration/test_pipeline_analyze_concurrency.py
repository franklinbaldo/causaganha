from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from causaganha.application.pipeline.analyze import run_analysis
from causaganha.domain.models import Intimation
from causaganha.domain.models_analysis import DecisionAnalysis, Outcome
from causaganha.infrastructure.storage.repositories.intimation import IntimationRepository


@pytest.mark.asyncio
async def test_run_analysis_concurrent_batch(tmp_path: Path) -> None:
    from causaganha.infrastructure.storage.connection import get_connection
    from causaganha.infrastructure.storage.schema import create_schema

    db_path = tmp_path / "test_concurrent.duckdb"
    con = get_connection(str(db_path))
    create_schema(con)
    repository = IntimationRepository(con)
    from causaganha.infrastructure.storage.repositories.analysis import AnalysisRepository

    analysis_repo = AnalysisRepository(con)

    # 1. Seed DB with multiple unanalyzed intimations
    intimations = []
    for i in range(5):
        intimations.append(
            Intimation(
                id=100 + i,
                numero_processo=f"proc-{i}",
                data_disponibilizacao=date(2024, 1, 1),
                sigla_tribunal="TJRO",
                tipo_comunicacao="INTIMAÇÃO",
                nome_orgao="Vara Cível",
                texto="Decisão.",
                link=f"http://example.com/doc-{i}.pdf",
                tipo_documento="Decisão",
                nome_classe="Procedimento Comum",
                hash=f"hash-{i}",
                status="ATIVO",
                advogados=[],
                partes=[],
            )
        )
    await repository.store_intimations(intimations)

    # 2. Mock DocumentService with delay to test concurrency
    mock_doc_service = AsyncMock()

    # 3. Mock Analyzer
    mock_analysis = DecisionAnalysis(
        outcome=Outcome.WIN,
        summary="Won",
        judge_name="Judge",
        confidence_score=0.9,
    )
    mock_analyzer = AsyncMock()
    mock_analyzer.analyze_bulk.return_value = [mock_analysis for _ in intimations]

    # Run with batch_size=5
    # The current implementation is sequential, so this will pass but slower.
    # We will refactor to make it concurrent.
    await run_analysis(
        repository=repository,
        analysis_repository=analysis_repo,
        doc_service=mock_doc_service,
        analyzer=mock_analyzer,
        limit=5,
        batch_size=5,
    )

    # Verify all were processed
    t = con.table("analysis_results")
    rows = t.execute()
    assert len(rows) == 5

    # Verify calls
    mock_doc_service.download_pdf.assert_not_called()
    mock_analyzer.analyze_bulk.assert_awaited_once()
