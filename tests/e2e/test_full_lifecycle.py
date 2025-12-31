"""End-to-end full lifecycle test for CausaGanha V2.

Verifies the complete flow: Collect -> DB -> Analyze -> Score -> Archive.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import ibis
import pytest

from causaganha.analysis.analyzer import DecisionAnalyzer
from causaganha.analysis.models import DecisionAnalysis, Outcome
from causaganha.api.client import PJeAPIClient
from causaganha.pipeline.analyze import run_analysis
from causaganha.pipeline.archive import run_archive
from causaganha.pipeline.collect import run_collection
from causaganha.pipeline.score import run_scoring
from causaganha.services.archive import InternetArchiveService
from causaganha.services.document import DocumentService
from causaganha.storage.connection import get_connection
from causaganha.storage.repository import IntimationRepository
from causaganha.storage.schema import create_schema


@pytest.fixture
def realistic_data() -> list[dict[str, Any]]:
    """Load realistic data from JSON."""
    data_path = Path("tests/mock_data/sample_intimacoes.json")
    if not data_path.exists():
        pytest.fail(f"Mock data not found at {data_path}")
    data = json.loads(data_path.read_text())
    # Return only the first 2 items to keep test fast and predictable
    return data["items"][:2]


@pytest.fixture
def db_connection() -> ibis.BaseBackend:
    """Create in-memory DuckDB connection."""
    con = get_connection(":memory:")
    create_schema(con)
    return con


@pytest.fixture
def repository(db_connection: ibis.BaseBackend) -> IntimationRepository:
    """Create repository."""
    return IntimationRepository(db_connection)


@pytest.mark.asyncio
async def test_full_lifecycle(
    db_connection: ibis.BaseBackend,
    repository: IntimationRepository,
    realistic_data: list[dict[str, Any]],
) -> None:
    """Test the complete lifecycle of CausaGanha V2.

    Flow:
      1. Collect: Fetch data from mocked PJe API and store in DB.
      2. Archive: Mock download and archive to mocked IA/Local storage.
      3. Analyze: Mock AI analysis of the archived document.
      4. Score: Calculate ratings based on analysis results.
    """
    # === STEP 1: COLLECTION ===
    # Mock API Client
    real_client = PJeAPIClient()
    mock_response = {
        "status": "success",
        "count": len(realistic_data),
        "items": realistic_data,
    }

    with patch.object(real_client.client, "get") as mock_get:
        # First page returns data, second page empty to stop pagination
        mock_get.side_effect = [
            MagicMock(json=lambda: mock_response, raise_for_status=lambda: None),
            MagicMock(json=lambda: {"items": []}, raise_for_status=lambda: None),
        ]

        await run_collection(
            repository=repository,
            client=real_client,
            start_date="2025-01-01",
            end_date="2025-01-07",
            courts=["TJRO"],
        )

    # Verify Collection
    intimations = await repository.get_unanalyzed_intimations(limit=100)
    assert len(intimations) == 2
    # Check for process number from sample_intimacoes.json (first item)
    # Item 0: 70127110520238220007
    assert "70127110520238220007" in [i["numero_processo"] for i in intimations]

    # === STEP 2: ARCHIVE ===
    # Mock DocumentService and ArchiveService
    mock_doc_service = MagicMock(spec=DocumentService)
    mock_doc_service.download_pdf.return_value = b"%PDF-1.4 dummy content"

    # Using LocalArchiveService for testing simplicity, or mock InternetArchiveService
    # Let's mock the upload method of whatever service is returned
    mock_archive_service = MagicMock(spec=InternetArchiveService)
    mock_archive_service.upload_file.return_value = (
        "https://archive.org/details/causaganha-tjro-12345"
    )

    await run_archive(
        repository=repository,
        doc_service=mock_doc_service,
        archive_service=mock_archive_service,
        limit=10,
        dry_run=False,
    )

    # Verify Archive - Check that 'ia_url' is updated in DB
    # Note: run_archive updates 'ia_url' in the database.
    # We can check the DB directly via Ibis
    intimations_table = db_connection.table("intimations")
    results = (
        intimations_table.filter(intimations_table.ia_url.notnull()).execute()
    )
    assert len(results) == 2
    assert results["ia_url"].iloc[0].startswith("https://archive.org/")

    # === STEP 3: ANALYZE ===
    # Mock Analyzer
    mock_analyzer = MagicMock(spec=DecisionAnalyzer)

    # Define outcomes
    analysis_results = [
        DecisionAnalysis(
            winner_lawyer_oab="6475A",
            winner_lawyer_state="RO",
            winner_party_name="JUAREZ MOREIRA DE SOUZA",
            loser_lawyer_oab="9999",
            loser_lawyer_state="RO",
            loser_party_name="BANCO X",
            decision_type="Sentença",
            outcome=Outcome.WIN,
            summary="Summary 1",
            judge_name="Dr. Judge",
            decision_reasoning="Reasoning...",
            confidence_score=0.95,
        ),
        DecisionAnalysis(
            winner_lawyer_oab="1234",
            winner_lawyer_state="RO",
            winner_party_name="BANCO DO BRASIL SA",
            loser_lawyer_oab="0000",
            loser_lawyer_state="RO",
            loser_party_name="JOAO DA SILVA",
            decision_type="Decisão",
            outcome=Outcome.WIN,
            summary="Summary 2",
            judge_name="Dr. Judge 2",
            decision_reasoning="Reasoning 2...",
            confidence_score=0.90,
        ),
    ]

    async def side_effect(*args: object, **kwargs: object) -> DecisionAnalysis:
        del args, kwargs  # Unused
        return analysis_results.pop(0)

    mock_analyzer.analyze_decision = AsyncMock(side_effect=side_effect)

    await run_analysis(
        repository=repository,
        doc_service=mock_doc_service,
        analyzer=mock_analyzer,
        limit=10,
    )

    # Verify Analysis - Check 'analysis_results' table
    analyzed_items = db_connection.table("analysis_results").execute()
    assert len(analyzed_items) == 2
    assert "6475A" in analyzed_items["winner_lawyer_oab"].values

    # === STEP 4: SCORE ===
    await run_scoring(
        repository=repository,
        limit=100,
    )

    # Verify Scoring - Check 'lawyer_ratings' table
    ratings = db_connection.table("lawyer_ratings").execute()
    assert len(ratings) > 0

    # Verify specific lawyer rating
    lawyer_a = ratings[ratings["oab_number"] == "6475A"].iloc[0]
    assert lawyer_a["wins"] == 1
    assert lawyer_a["mu"] > 25.0  # Default mu is 25, win increases it
