from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from causaganha.analysis.models import DecisionAnalysis, Outcome
from causaganha.pipeline.analyze import run_analysis


@pytest.mark.asyncio
async def test_run_analysis_success(tmp_path: Path) -> None:
    from causaganha.api.models import Intimation
    from causaganha.storage.connection import get_connection
    from causaganha.storage.queries import store_intimations
    from causaganha.storage.schema import create_schema

    db_path = tmp_path / "test.duckdb"
    con = get_connection(str(db_path))
    create_schema(con)

    # 1. Seed DB with unanalyzed intimation
    intimation = Intimation(
        id=100,
        numero_processo="1234567-89.2024.8.00.0000",
        data_disponibilizacao="2024-01-01",
        siglaTribunal="TJRO",
        tipoComunicacao="INTIMAÇÃO",
        nomeOrgao="Vara Cível",
        texto="Decisão.",
        link="http://example.com/decision.pdf",
        tipoDocumento="Decisão",
        nomeClasse="Procedimento Comum",
        hash="abc123hash",
        status="ATIVO",
    )
    await store_intimations(con, [intimation])

    # 2. Mock Download
    with patch("causaganha.pipeline.analyze.download_pdf", new_callable=AsyncMock) as mock_download:
        mock_download.return_value = b"%PDF-1.5 fake content"

        # 3. Mock Analyzer
        mock_analysis = DecisionAnalysis(
            outcome=Outcome.WIN,
            summary="Won",
            judge_name="Judge",
            confidence_score=0.9,
        )

        # We need to patch DecisionAnalyzer class
        with patch("causaganha.pipeline.analyze.DecisionAnalyzer") as mock_analyzer_cls:
            mock_analyzer_instance = mock_analyzer_cls.return_value
            mock_analyzer_instance.analyze_decision = AsyncMock(return_value=mock_analysis)

            # Run
            await run_analysis(db_path=str(db_path), limit=1)

            # Verify
            mock_download.assert_called_with("http://example.com/decision.pdf")
            mock_analyzer_instance.analyze_decision.assert_called_once()

            # Check DB
            t = con.table("analysis_results")
            rows = t.execute()
            assert len(rows) == 1
            assert rows.iloc[0]["intimation_id"] == 100
            assert rows.iloc[0]["outcome"] == "WIN"
