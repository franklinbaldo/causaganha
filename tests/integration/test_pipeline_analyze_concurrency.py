import asyncio
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from causaganha.analysis.models import DecisionAnalysis, Outcome
from causaganha.domain.models import Intimation
from causaganha.pipeline.analyze import run_analysis
from causaganha.storage.repository import IntimationRepository


@pytest.mark.asyncio
async def test_run_analysis_concurrent_batch(tmp_path: Path) -> None:
    from causaganha.storage.connection import get_connection
    from causaganha.storage.schema import create_schema

    db_path = tmp_path / "test_concurrent.duckdb"
    con = get_connection(str(db_path))
    create_schema(con)
    repository = IntimationRepository(con)

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
            ),
        )
    await repository.store_intimations(intimations)

    # 2. Mock DocumentService with delay to test concurrency
    mock_doc_service = AsyncMock()

    async def download_with_delay(url):
        await asyncio.sleep(0.01)
        return b"%PDF-1.5 fake content"

    mock_doc_service.download_pdf.side_effect = download_with_delay

    # 3. Mock Analyzer
    mock_analysis = DecisionAnalysis(
        outcome=Outcome.WIN,
        summary="Won",
        judge_name="Judge",
        confidence_score=0.9,
    )
    mock_analyzer = AsyncMock()
    mock_analyzer.analyze_decision.return_value = mock_analysis

    # Run with batch_size=5
    # The current implementation is sequential, so this will pass but slower.
    # We will refactor to make it concurrent.
    await run_analysis(
        repository=repository,
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
    assert mock_doc_service.download_pdf.call_count == 5
    assert mock_analyzer.analyze_decision.call_count == 5
