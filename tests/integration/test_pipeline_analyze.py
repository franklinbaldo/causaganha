from pathlib import Path
from unittest.mock import AsyncMock, patch
from datetime import date

import pytest

from causaganha.analysis.models import DecisionAnalysis, Outcome
from causaganha.pipeline.analyze import run_analysis
from causaganha.domain.models import Intimation


@pytest.fixture
def db_setup(tmp_path: Path):
    from causaganha.storage.connection import get_connection
    from causaganha.storage.schema import create_schema

    db_path = tmp_path / "test.duckdb"
    con = get_connection(str(db_path))
    create_schema(con)
    return db_path, con


@pytest.mark.asyncio
async def test_run_analysis_success(db_setup) -> None:
    from causaganha.storage.queries import store_intimations

    db_path, con = db_setup

    # 1. Seed DB with unanalyzed intimation
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
            winner_lawyer_oab="12345",
            winner_lawyer_state="RO",
            loser_lawyer_oab="67890",
            loser_lawyer_state="RO"
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


@pytest.mark.asyncio
async def test_run_analysis_download_failure(db_setup) -> None:
    from causaganha.storage.queries import store_intimations

    db_path, con = db_setup

    intimation = Intimation(
        id=101,
        numero_processo="1234567-89.2024.8.00.0001",
        data_disponibilizacao=date(2024, 1, 1),
        sigla_tribunal="TJRO",
        tipo_comunicacao="INTIMAÇÃO",
        nome_orgao="Vara Cível",
        texto="Decisão.",
        link="http://example.com/fail.pdf",
        tipo_documento="Decisão",
        nome_classe="Procedimento Comum",
        hash="failhash",
        status="ATIVO",
    )
    await store_intimations(con, [intimation])

    with patch("causaganha.pipeline.analyze.download_pdf", new_callable=AsyncMock) as mock_download:
        mock_download.return_value = None  # Simulate download failure

        with patch("causaganha.pipeline.analyze.DecisionAnalyzer") as mock_analyzer_cls:
            mock_analyzer_instance = mock_analyzer_cls.return_value

            await run_analysis(db_path=str(db_path), limit=1)

            mock_download.assert_called_with("http://example.com/fail.pdf")
            mock_analyzer_instance.analyze_decision.assert_not_called()

            t = con.table("analysis_results")
            rows = t.execute()
            assert len(rows) == 1
            assert rows.iloc[0]["intimation_id"] == 101
            assert rows.iloc[0]["outcome"] == "UNKNOWN"
            assert "Download failed" in rows.iloc[0]["summary"]


@pytest.mark.asyncio
async def test_run_analysis_analyzer_failure(db_setup) -> None:
    from causaganha.storage.queries import store_intimations

    db_path, con = db_setup

    intimation = Intimation(
        id=102,
        numero_processo="1234567-89.2024.8.00.0002",
        data_disponibilizacao=date(2024, 1, 1),
        sigla_tribunal="TJRO",
        tipo_comunicacao="INTIMAÇÃO",
        nome_orgao="Vara Cível",
        texto="Decisão.",
        link="http://example.com/error.pdf",
        tipo_documento="Decisão",
        nome_classe="Procedimento Comum",
        hash="errorhash",
        status="ATIVO",
    )
    await store_intimations(con, [intimation])

    with patch("causaganha.pipeline.analyze.download_pdf", new_callable=AsyncMock) as mock_download:
        mock_download.return_value = b"%PDF-1.5 error content"

        with patch("causaganha.pipeline.analyze.DecisionAnalyzer") as mock_analyzer_cls:
            mock_analyzer_instance = mock_analyzer_cls.return_value
            mock_analyzer_instance.analyze_decision.side_effect = Exception("AI Error")

            await run_analysis(db_path=str(db_path), limit=1)

            t = con.table("analysis_results")
            rows = t.execute()
            assert len(rows) == 1
            assert rows.iloc[0]["intimation_id"] == 102
            assert rows.iloc[0]["outcome"] == "UNKNOWN"
            assert "Analysis failed" in rows.iloc[0]["summary"]
