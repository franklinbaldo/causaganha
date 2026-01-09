"""Integration test using realistic JSON data to simulate the full pipeline."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from causaganha.analysis.analyzer import DecisionAnalyzer
from causaganha.analysis.models import DecisionAnalysis
from causaganha.api.client import PJeAPIClient
from causaganha.pipeline.analyze import run_analysis
from causaganha.pipeline.collect import run_collection
from causaganha.pipeline.score import run_scoring
from causaganha.services.document import DocumentService
from causaganha.storage.connection import get_connection
from causaganha.storage.repositories.analysis import AnalysisRepository
from causaganha.storage.repositories.intimation import IntimationRepository
from causaganha.storage.repositories.lawyer import LawyerRatingRepository
from causaganha.storage.schema import create_schema


@pytest.fixture
def realistic_data():
    """Load realistic data from JSON."""
    data_path = Path("tests/mock_data/sample_intimacoes.json")
    if not data_path.exists():
        pytest.fail(f"Mock data not found at {data_path}")
    data = json.loads(data_path.read_text())
    # Return just the items list
    return data.get("items", [])


@pytest.fixture
def db_connection():
    """Create in-memory DuckDB connection."""
    con = get_connection(":memory:")
    create_schema(con)
    return con


@pytest.fixture
def repository(db_connection):
    """Create repository."""
    return IntimationRepository(db_connection)


@pytest.mark.asyncio
async def test_pipeline_with_realistic_data(db_connection, repository, realistic_data) -> None:
    """Test the full pipeline (Collect -> Analyze -> Score) using realistic JSON data.
    Mocking:
      - API Client: returns the JSON data.
      - Document Service: returns dummy PDF bytes.
      - Analyzer: returns a dummy DecisionAnalysis object.
    """
    analysis_repo = AnalysisRepository(db_connection)
    rating_repo = LawyerRatingRepository(db_connection)

    # --- STAGE 1: COLLECTION ---

    # Mock API Client to return realistic data
    MagicMock(spec=PJeAPIClient)

    real_client = PJeAPIClient()

    # Prepare the mock response structure
    mock_response = {
        "status": "success",
        "count": len(realistic_data),
        "items": realistic_data,
    }

    with patch.object(real_client.client, "get") as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.raise_for_status = lambda: None
        # Mock getting an empty list for the second page to stop pagination
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

    # DEBUG: Check table content directly
    all_intimations = await repository.get_all_intimations()
    print(f"DEBUG: Total intimations in DB: {len(all_intimations)}")
    if len(all_intimations) > 0:
        print(f"DEBUG: Sample intimation: {all_intimations[0]}")

    # Verify Collection - limit to 300 (total in file)
    intimations = await repository.get_unanalyzed_intimations(limit=300)
    # The file has 300 items, but run_collection might deduplicate or filter.
    # We assert at least some were stored.
    assert len(intimations) > 0

    # Verify Lawyer Association
    # (Checking DB directly via Ibis to ensure table population)
    lawyers = db_connection.table("intimation_lawyers").execute()
    assert len(lawyers) > 0

    # --- STAGE 2: ANALYSIS ---

    # Mock Document Service
    mock_doc_service = MagicMock(spec=DocumentService)
    mock_doc_service.download_pdf.return_value = b"%PDF-1.4 dummy content"

    # Mock Analyzer
    mock_analyzer = MagicMock(spec=DecisionAnalyzer)

    # Return different results for the two intimations
    from causaganha.analysis.models import Outcome

    # Create enough results for the limit
    analysis_results = [
        DecisionAnalysis(
            winner_lawyer_oab="6475A",
            winner_lawyer_state="RO",
            winner_party_name="JUAREZ MOREIRA DE SOUZA",
            loser_lawyer_oab="9999", # Unknown/Other
            loser_lawyer_state="RO",
            loser_party_name="BANCO X",
            decision_type="Sentença",
            outcome=Outcome.WIN,
            summary=f"Summary {i}",
            judge_name="Dr. Judge",
            decision_reasoning="Reasoning...",
            confidence_score=0.95,
        ) for i in range(10)
    ]

    # The pipeline calls analyze_decision (via process_item)
    mock_analyzer.analyze_decision = AsyncMock(side_effect=analysis_results)

    await run_analysis(
        repository=repository,
        analysis_repository=analysis_repo,
        doc_service=mock_doc_service,
        analyzer=mock_analyzer,
        limit=10,
    )

    # Verify Analysis Storage
    analyzed_items = db_connection.table("analysis_results").execute()
    assert len(analyzed_items) == 10
    assert "6475A" in analyzed_items["winner_lawyer_oab"].values

    # --- STAGE 3: SCORING ---

    await run_scoring(
        analysis_repository=analysis_repo,
        rating_repository=rating_repo,
        limit=100,
    )

    # Verify Ratings
    ratings = db_connection.table("lawyer_ratings").execute()
    assert len(ratings) > 0

    # Lawyer 6475A won, so mu should be > 25
    lawyer_a = ratings[ratings["oab_number"] == "6475A"].iloc[0]
    assert lawyer_a["mu"] > 25.0
    assert lawyer_a["wins"] >= 1
