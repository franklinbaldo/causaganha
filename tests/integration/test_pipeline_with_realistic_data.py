"""Integration test using realistic JSON data to simulate the full pipeline."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from causaganha.api.client import PJeAPIClient
from causaganha.pipeline.collect import run_collection
from causaganha.pipeline.analyze import run_analysis
from causaganha.pipeline.score import run_scoring
from causaganha.storage.connection import get_connection
from causaganha.storage.repository import IntimationRepository
from causaganha.storage.schema import create_schema
from causaganha.services.document import DocumentService
from causaganha.analysis.analyzer import DecisionAnalyzer
from causaganha.analysis.models import DecisionAnalysis


@pytest.fixture
def realistic_data():
    """Load realistic data from JSON."""
    data_path = Path("tests/mock_data/realistic_intimations.json")
    if not data_path.exists():
        pytest.fail(f"Mock data not found at {data_path}")
    return json.loads(data_path.read_text())


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
async def test_pipeline_with_realistic_data(db_connection, repository, realistic_data):
    """
    Test the full pipeline (Collect -> Analyze -> Score) using realistic JSON data.
    Mocking:
      - API Client: returns the JSON data.
      - Document Service: returns dummy PDF bytes.
      - Analyzer: returns a dummy DecisionAnalysis object.
    """

    # --- STAGE 1: COLLECTION ---

    # Mock API Client to return realistic data
    mock_client = MagicMock(spec=PJeAPIClient)

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
        "items": realistic_data
    }

    with patch.object(real_client.client, 'get') as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.raise_for_status = lambda: None
        # Mock getting an empty list for the second page to stop pagination
        mock_get.side_effect = [
             MagicMock(json=lambda: mock_response, raise_for_status=lambda: None),
             MagicMock(json=lambda: {"items": []}, raise_for_status=lambda: None)
        ]

        await run_collection(
            repository=repository,
            client=real_client,
            start_date="2025-01-01",
            end_date="2025-01-07",
            courts=["TJRO"]
        )

    # Verify Collection
    intimations = await repository.get_unanalyzed_intimations(limit=100)
    assert len(intimations) == 2
    # Verify the first intimation process number (allowing for random order in list)
    process_numbers = [i['numero_processo'] for i in intimations]
    assert "70009673320258220010" in process_numbers

    # Verify Lawyer Association
    # (Checking DB directly via Ibis to ensure table population)
    lawyers = db_connection.table("intimation_lawyers").execute()
    assert len(lawyers) > 0
    assert "6475A" in lawyers["oab_number"].values

    # --- STAGE 2: ANALYSIS ---

    # Mock Document Service
    mock_doc_service = MagicMock(spec=DocumentService)
    mock_doc_service.download_pdf.return_value = b"%PDF-1.4 dummy content"

    # Mock Analyzer
    mock_analyzer = MagicMock(spec=DecisionAnalyzer)

    # Return different results for the two intimations
    from causaganha.analysis.models import Outcome

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
                summary="Summary 1",
            judge_name="Dr. Judge",
            decision_reasoning="Reasoning...",
            confidence_score=0.95
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
            confidence_score=0.90
        )
    ]

    # The pipeline calls analyze_decision (via process_item)
    mock_analyzer.analyze_decision = AsyncMock(side_effect=analysis_results)

    await run_analysis(
        repository=repository,
        doc_service=mock_doc_service,
        analyzer=mock_analyzer,
        limit=10
    )

    # Verify Analysis Storage
    analyzed_items = db_connection.table("analysis_results").execute()
    assert len(analyzed_items) == 2
    assert "6475A" in analyzed_items["winner_lawyer_oab"].values

    # --- STAGE 3: SCORING ---

    await run_scoring(
        repository=repository,
        limit=100
    )

    # Verify Ratings
    ratings = db_connection.table("lawyer_ratings").execute()
    assert len(ratings) > 0

    # Lawyer 6475A won, so mu should be > 25
    lawyer_a = ratings[ratings["oab_number"] == "6475A"].iloc[0]
    assert lawyer_a["mu"] > 25.0
    assert lawyer_a["wins"] == 1
