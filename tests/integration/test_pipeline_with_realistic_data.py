"""Integration test using realistic JSON data to simulate the full pipeline."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from causaganha.analysis.analyzer import DecisionAnalyzer
from causaganha.analysis.models import DecisionAnalysis
from causaganha.integrations.pje.client import PJeAPIClient
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
    data_path = Path("tests/mock_data/realistic_intimations.json")
    if not data_path.exists():
        pytest.fail(f"Mock data not found at {data_path}")
    data = json.loads(data_path.read_text())
    return data["items"]


@pytest.fixture
def db_connection():
    """Create in-memory DuckDB connection."""
    con = get_connection(":memory:")
    create_schema(con)
    return con


@pytest.fixture
def repository(db_connection):
    """Create intimation repository."""
    return IntimationRepository(db_connection)


@pytest.fixture
def analysis_repository(db_connection):
    """Create analysis repository."""
    return AnalysisRepository(db_connection)


@pytest.fixture
def rating_repository(db_connection):
    """Create rating repository."""
    return LawyerRatingRepository(db_connection)


@pytest.mark.asyncio
async def test_pipeline_with_realistic_data(
    db_connection,
    repository,
    analysis_repository,
    rating_repository,
    realistic_data,
) -> None:
    """Test the full pipeline (Collect -> Analyze -> Score) using realistic JSON data.
    Mocking:
      - API Client: returns the JSON data.
      - Document Service: returns dummy PDF bytes.
      - Analyzer: returns a dummy DecisionAnalysis object.
    """
    # --- STAGE 1: COLLECTION ---

    # Mock API Client to return realistic data
    MagicMock(spec=PJeAPIClient)

    # We need to structure the return value of get_intimations_by_court to return Domain Models
    # Since PJeAPIClient._map_to_domain is internal, we can rely on PJeAPIClient behavior if we mock the HTTP layer,
    # OR we can mock get_intimations_by_court directly to return a list of DomainIntimation.
    # Given we want to test "Integration", mocking the HTTP layer is better to exercise the Client mapping logic.
    # However, `PJeAPIClient` uses `httpx.AsyncClient`.

    # Let's mock the `get_intimations_by_court` for simplicity and robustness in this test,
    # ensuring we are testing the PIPELINE logic, not the CLIENT logic (which has its own unit tests).

    # Actually, to use `realistic_data` (which is API JSON format), we should probably use the real `PJeAPIClient`
    # and mock the `httpx` response. This verifies the mapping logic too.

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

    # Verify Collection
    intimations = await repository.get_unanalyzed_intimations(limit=300)
    assert len(intimations) == 300
    # Verify the first intimation process number (allowing for random order in list)
    process_numbers = [i.numero_processo for i in intimations]
    assert "70127110520238220007" in process_numbers

    # Verify Lawyer Association
    # (Checking DB directly via Ibis to ensure table population)
    lawyers = db_connection.table("intimation_lawyers").execute()
    assert len(lawyers) > 0
    assert "9173" in lawyers["oab_number"].values

    # --- STAGE 2: ANALYSIS ---

    # Mock Document Service
    mock_doc_service = MagicMock(spec=DocumentService)
    mock_doc_service.download_pdf.return_value = b"%PDF-1.4 dummy content"

    # Mock Analyzer
    mock_analyzer = MagicMock(spec=DecisionAnalyzer)

    # Return valid result
    from causaganha.analysis.models import Outcome

    # Use return_value instead of side_effect to handle any number of calls
    mock_analyzer.analyze_decision = AsyncMock(return_value=DecisionAnalysis(
        winner_lawyer_oab="9173",
        winner_lawyer_state="ES",
        winner_party_name="BANCO DO BRASIL SA",
        loser_lawyer_oab="9999", # Unknown/Other
        loser_lawyer_state="RO",
        loser_party_name="CLAUD INEI SCOTTI",
        decision_type="Sentença",
        outcome=Outcome.WIN,
        summary="Summary Generic",
        judge_name="Dr. Judge",
        decision_reasoning="Reasoning...",
        confidence_score=0.95,
    ))

    await run_analysis(
        repository=repository,
        analysis_repository=analysis_repository,
        doc_service=mock_doc_service,
        analyzer=mock_analyzer,
        limit=10,
    )

    # Verify Analysis Storage
    analyzed_items = db_connection.table("analysis_results").execute()
    assert len(analyzed_items) == 10
    assert "9173" in analyzed_items["winner_lawyer_oab"].values

    # --- STAGE 3: SCORING ---

    await run_scoring(
        analysis_repository=analysis_repository,
        rating_repository=rating_repository,
        limit=100,
    )

    # Verify Ratings
    ratings = db_connection.table("lawyer_ratings").execute()
    assert len(ratings) > 0

    # Lawyer 9173 won, so mu should be > 25
    lawyer_a = ratings[ratings["oab_number"] == "9173"].iloc[0]
    assert lawyer_a["mu"] > 25.0
    # Wins might be > 1 if multiple cases were analyzed for same lawyer
    assert lawyer_a["wins"] >= 1
