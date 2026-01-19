"""Integration test script for V2 pipeline."""

import asyncio
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import structlog

from causaganha.analysis.analyzer import DecisionAnalyzer
from causaganha.analysis.models import DecisionAnalysis, Outcome
from causaganha.api.client import PJeAPIClient
from causaganha.domain.models import Intimation, Lawyer
from causaganha.pipeline.analyze import run_analysis
from causaganha.pipeline.collect import run_collection
from causaganha.pipeline.score import run_scoring
from causaganha.services.document import DocumentService
from causaganha.storage.connection import get_connection
from causaganha.storage.repository import IntimationRepository
from causaganha.storage.schema import create_schema


logger = structlog.get_logger()


async def main() -> None:
    """Run the integration test pipeline."""
    # Setup test environment
    test_db_path = "data/integration_test.duckdb"
    if Path(test_db_path).exists():
        Path(test_db_path).unlink()

    # Ensure data directory exists
    Path(test_db_path).parent.mkdir(parents=True, exist_ok=True)

    # 1. Mock External Services

    # Mock API Response
    today = date.today()
    yesterday = today - timedelta(days=1)

    mock_intimation = Intimation(
        id=1001,
        numero_processo="0001001-00.2024.8.22.0001",
        numero_processo_formatado="0001001-00.2024.8.22.0001",
        data_disponibilizacao=today,
        sigla_tribunal="TJRO",
        tipo_comunicacao="Intimação",
        nome_orgao="1ª Vara Cível",
        texto="Intimação de sentença...",
        link="http://example.com/doc1.pdf",
        tipo_documento="Sentença",
        nome_classe="Procedimento Comum",
        codigo_classe="7",
        hash="abc1",
        status="P",
        advogados=[
            Lawyer(id=1, nome="Advogado A", numero_oab="1001", uf_oab="RO"),
            Lawyer(id=2, nome="Advogado B", numero_oab="1002", uf_oab="RO"),
        ],
        partes=[],
    )

    # Mock Analysis Result
    mock_analysis = DecisionAnalysis(
        winner_lawyer_oab="1001",
        winner_lawyer_state="RO",
        winner_party_name="Winner",
        loser_lawyer_oab="1002",
        loser_lawyer_state="RO",
        loser_party_name="Loser",
        decision_type="Sentença",
        outcome=Outcome.WIN,
        summary="Test summary",
        judge_name="Judge Test",
        decision_reasoning="Reasoning test",
        confidence_score=0.95,
    )

    # 2. Run Pipeline Stages

    logger.info("Starting Integration Test Pipeline")

    # Connect to DB and Initialize Schema
    con = get_connection(test_db_path)
    create_schema(con)
    repo = IntimationRepository(con)

    # --- STAGE 1: COLLECTION ---
    logger.info("Running Collection Stage...")

    with patch(
        "causaganha.api.client.PJeAPIClient.get_intimations_by_court", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = [mock_intimation]

        client = PJeAPIClient()
        await run_collection(
            client=client,
            repository=repo,
            courts=["TJRO"],
            start_date=yesterday.isoformat(),
            end_date=today.isoformat(),
        )

    # Verify Collection
    intimations = con.table("intimations").execute()
    assert len(intimations) == 1
    assert intimations.iloc[0]["id"] == 1001
    logger.info("Collection Stage Verified")

    # --- STAGE 2: ANALYSIS ---
    logger.info("Running Analysis Stage...")

    # Mock Document Service
    doc_service = DocumentService()
    doc_service.download_pdf = AsyncMock(return_value=b"%PDF-1.4...")  # type: ignore

    # Mock Analyzer
    with patch("causaganha.analysis.analyzer.Agent") as mock_agent_cls:
        analyzer = DecisionAnalyzer(model="google-gla:gemini-2.5-flash")
        analyzer.analyze_decision = AsyncMock(return_value=mock_analysis)  # type: ignore

        await run_analysis(
            repository=repo,
            doc_service=doc_service,
            analyzer=analyzer,
            limit=10,
        )

    # Verify Analysis
    analyses = con.table("analysis_results").execute()
    assert len(analyses) == 1
    assert analyses.iloc[0]["intimation_id"] == 1001

    # Check outcome - expecting "WIN" based on Enum definition
    assert analyses.iloc[0]["outcome"] == "WIN"

    logger.info("Analysis Stage Verified")

    # --- STAGE 3: SCORING ---
    logger.info("Running Scoring Stage...")

    await run_scoring(
        repository=repo,
        limit=100,
    )

    # Verify Scoring
    # Verify 'lawyer_ratings' table exists and has entries

    ratings = con.table("lawyer_ratings").execute()
    assert len(ratings) >= 2  # Winner and Loser

    winner = ratings[ratings["oab_number"] == "1001"].iloc[0]
    loser = ratings[ratings["oab_number"] == "1002"].iloc[0]

    # Check values - default mu is 25.0
    # Winner should be > 25, Loser should be < 25
    assert winner["mu"] > 25.0, f"Winner mu should be > 25, got {winner['mu']}"
    assert loser["mu"] < 25.0, f"Loser mu should be < 25, got {loser['mu']}"

    logger.info("Scoring Stage Verified")

    logger.info("Integration Test Completed Successfully!")

    # Cleanup
    if Path(test_db_path).exists():
        Path(test_db_path).unlink()


if __name__ == "__main__":
    asyncio.run(main())
