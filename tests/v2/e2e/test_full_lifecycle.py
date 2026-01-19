"""End-to-end test for the full lifecycle of CausaGanha V2."""

from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from ibis.backends.duckdb import Backend

from causaganha.v2.analysis.models import DecisionAnalysis
from causaganha.v2.api.client import Intimation
from causaganha.v2.pipeline.collect import collect_metadata_for_court
from causaganha.v2.pipeline.analyze import analyze_pending_decisions
from causaganha.v2.pipeline.score import calculate_ratings
from causaganha.v2.pipeline.archive import archive_documents


@pytest.fixture
def mock_intimations() -> list[Intimation]:
    """Provide mock intimations for E2E test."""
    return [
        Intimation(
            id=1001,
            numero_processo="1001-89.2024.8.22.0001",
            siglaTribunal="TJRO",
            data_disponibilizacao="2024-01-01",
            link="http://example.com/1001.pdf",
            destinatarioadvogados=[
                {
                    "advogado": {
                        "id": 1,
                        "nome": "LAWYER WINNER",
                        "numero_oab": "1000",
                        "uf_oab": "RO"
                    }
                },
                {
                    "advogado": {
                        "id": 2,
                        "nome": "LAWYER LOSER",
                        "numero_oab": "2000",
                        "uf_oab": "RO"
                    }
                }
            ]
        ),
    ]


@pytest.fixture
def mock_analysis() -> DecisionAnalysis:
    """Provide mock decision analysis for E2E test."""
    return DecisionAnalysis(
        winner_lawyer_oab="1000",
        winner_lawyer_state="RO",
        winner_party_name="Winner Party",
        loser_lawyer_oab="2000",
        loser_lawyer_state="RO",
        loser_party_name="Loser Party",
        decision_type="sentença",
        outcome="procedente",
        judge_name="Judge Dredd",
        decision_reasoning="The law is the law.",
        confidence_score=0.95,
    )


@pytest.mark.asyncio
async def test_full_lifecycle_mocked(
    db_connection: Backend,
    mock_intimations: list[Intimation],
    mock_analysis: DecisionAnalysis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Test the full lifecycle from collection to archiving.

    Stages:
    1. Collect metadata from mocked PJe API.
    2. Analyze pending decisions using mocked Pydantic AI.
    3. Calculate ratings using OpenSkill (real logic, DB interaction).
    4. Archive documents using mocked PreservationService.
    """
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    # --- STAGE 1: COLLECTION ---
    print("\n[E2E] Starting Stage 1: Collection")
    with patch("causaganha.v2.pipeline.collect.PJeAPIClient") as mock_client_cls:
        client_instance = mock_client_cls.return_value
        client_instance.get_intimations_by_court = AsyncMock(
            return_value=mock_intimations,
        )
        client_instance.close = AsyncMock()

        collect_result = await collect_metadata_for_court("TJRO", days_back=1)

        assert collect_result["status"] == "success"
        assert collect_result["intimations_new"] == 1
        assert collect_result["lawyers_stored"] > 0

        # Verify DB state
        t_intimations = db_connection.table("intimations")
        res_intimations = t_intimations.execute()
        assert len(res_intimations) == 1
        assert res_intimations.iloc[0]["id"] == 1001
        assert not res_intimations.iloc[0]["analyzed"]

        t_lawyers = db_connection.table("intimation_lawyers")
        res_lawyers = t_lawyers.execute()
        assert len(res_lawyers) >= 2

    # --- STAGE 2: ANALYSIS ---
    print("[E2E] Starting Stage 2: Analysis")
    with patch("causaganha.v2.pipeline.analyze.DecisionAnalyzer") as mock_analyzer_cls:
        analyzer_instance = mock_analyzer_cls.return_value
        # analyzer_instance.analyze_batch must return a list of DecisionAnalysis or Exception
        analyzer_instance.analyze_batch = AsyncMock(return_value=[mock_analysis])

        analyze_result = await analyze_pending_decisions(batch_size=10)

        assert analyze_result["status"] == "success"
        assert analyze_result["analyzed"] == 1

        # Verify DB state
        t_analysis = db_connection.table("decision_analysis")
        res_analysis = t_analysis.execute()
        assert len(res_analysis) == 1
        assert res_analysis.iloc[0]["winner_lawyer_oab"] == "1000"

        # Verify intimation marked as analyzed
        res_intimations = t_intimations.execute()
        assert res_intimations.iloc[0]["analyzed"]

    # --- STAGE 3: SCORING ---
    print("[E2E] Starting Stage 3: Scoring")
    # No mocks needed for scoring logic as it uses internal DB and openskill
    score_result = await calculate_ratings(batch_size=10)

    assert score_result["status"] == "success"
    assert score_result["processed"] == 1

    # Verify ratings updated
    t_ratings = db_connection.table("lawyer_ratings")
    res_ratings = t_ratings.execute()
    assert len(res_ratings) == 2  # Winner and Loser

    # Check Winner stats
    winner = res_ratings[
        (res_ratings["oab_number"] == "1000") &
        (res_ratings["oab_state"] == "RO")
    ].iloc[0]
    assert winner["wins"] == 1
    assert winner["losses"] == 0
    assert winner["total_cases"] == 1
    # Initial mu=25, should increase
    assert winner["mu"] > 25.0

    # Check Loser stats
    loser = res_ratings[
        (res_ratings["oab_number"] == "2000") &
        (res_ratings["oab_state"] == "RO")
    ].iloc[0]
    assert loser["wins"] == 0
    assert loser["losses"] == 1
    assert loser["total_cases"] == 1
    # Initial mu=25, should decrease
    assert loser["mu"] < 25.0

    # --- STAGE 4: ARCHIVE ---
    print("[E2E] Starting Stage 4: Archive")
    mock_doc_service = MagicMock()
    mock_archive_service = MagicMock()

    # Mock generating metadata
    mock_archive_service.generate_metadata.return_value = {"title": "Test Doc"}

    # Mock preservation service which is used inside archive_documents
    # Since we can't easily patch the internal instantiation of PreservationService inside the function without touching the code,
    # or unless we patch the class in the module `causaganha.v2.pipeline.archive`.

    with patch("causaganha.v2.pipeline.archive.PreservationService") as mock_preservation_cls:
        preservation_instance = mock_preservation_cls.return_value
        preservation_instance.preserve_document = AsyncMock(
            return_value="https://archive.org/details/causaganha-tjro-1001"
        )

        archive_result = await archive_documents(
            doc_service=mock_doc_service,
            archive_service=mock_archive_service,
            limit=10,
            dry_run=False
        )

        assert archive_result["status"] == "success"
        assert archive_result["archived"] == 1

        # Verify DB updated with IA URL
        res_intimations = t_intimations.execute()
        assert res_intimations.iloc[0]["ia_url"] == "https://archive.org/details/causaganha-tjro-1001"
