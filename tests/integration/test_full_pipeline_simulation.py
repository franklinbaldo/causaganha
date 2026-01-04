"""End-to-end test simulating the full pipeline."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from causaganha.domain.models import Intimation, Lawyer
from causaganha.pipeline.analyze import run_analysis
from causaganha.pipeline.archive import run_archive
from causaganha.pipeline.collect import run_collection
from causaganha.pipeline.score import run_scoring
from causaganha.storage.repository import IntimationRepository
from causaganha.storage.repositories.lawyer import LawyerRatingRepository
from datetime import date


class TestFullPipelineSimulation:
    """Simulates the data flow from Collect -> Archive -> Analyze -> Score."""

    @pytest.fixture
    def mock_repo(self):
        repo = AsyncMock(spec=IntimationRepository)
        return repo

    @pytest.fixture
    def mock_lawyer_repo(self):
        repo = AsyncMock(spec=LawyerRatingRepository)
        return repo

    @pytest.fixture
    def mock_services(self):
        return {
            "client": AsyncMock(),
            "doc_service": AsyncMock(),
            "archive_service": AsyncMock(),
            "analyzer": AsyncMock(),
        }

    @pytest.mark.asyncio
    async def test_complete_pipeline_collect_to_score(self, mock_repo, mock_lawyer_repo, mock_services):
        # ---------------------------------------------------------
        # 1. Collect
        # ---------------------------------------------------------
        # Setup API response
        api_intimation = Intimation(
            id=100,
            numero_processo="123",
            data_disponibilizacao=date(2024, 1, 1),
            sigla_tribunal="TJRO",
            tipo_comunicacao="Int",
            nome_orgao="Vara",
            texto="Txt",
            link="http://pdf",
            tipo_documento="Doc",
            nome_classe="Class",
            hash="abc",
            status="P",
            advogados=[Lawyer(id=1, nome="Adv", numero_oab="123", uf_oab="RO")]
        )
        mock_services["client"].get_intimations_by_court.return_value = [api_intimation]

        # Run Collect
        await run_collection(mock_repo, mock_services["client"], "2024-01-01", "2024-01-01", ["TJRO"])

        # Verify
        mock_repo.store_intimations.assert_called_once()
        assert mock_repo.store_intimations.call_args[0][0][0].id == 100

        # ---------------------------------------------------------
        # 2. Archive
        # ---------------------------------------------------------
        # Setup repo to return the collected item as unarchived
        # (State change simulation)
        mock_repo.get_unarchived_intimations.return_value = [api_intimation]
        mock_services["doc_service"].download_pdf.return_value = b"PDF"
        mock_services["archive_service"].upload_file.return_value = "http://ia/item"
        mock_services["archive_service"].generate_metadata.return_value = {}

        # Run Archive
        await run_archive(mock_repo, mock_services["doc_service"], mock_services["archive_service"])

        # Verify
        mock_services["archive_service"].upload_file.assert_called()
        mock_repo.mark_as_archived.assert_called_with("100", "http://ia/item")

        # ---------------------------------------------------------
        # 3. Analyze
        # ---------------------------------------------------------
        # Setup repo to return unanalyzed item
        mock_repo.get_unanalyzed_intimations.return_value = [api_intimation]
        # Setup analyzer response
        analysis_result = AsyncMock()
        analysis_result.outcome.value = "WIN"
        analysis_result.winner_lawyer_oab = "123"
        analysis_result.winner_lawyer_state = "RO"
        analysis_result.loser_lawyer_oab = "456"
        analysis_result.loser_lawyer_state = "RO"
        analysis_result.summary = "Summary"
        analysis_result.judge_name = "Judge"
        analysis_result.confidence_score = 0.9
        analysis_result.decision_type = "Type"
        analysis_result.decision_reasoning = "Reason"
        analysis_result.winner_party_name = "Winner"
        analysis_result.loser_party_name = "Loser"

        mock_services["analyzer"].analyze_decision.return_value = analysis_result

        # Run Analyze
        await run_analysis(mock_repo, mock_services["doc_service"], mock_services["analyzer"])

        # Verify
        mock_repo.store_analysis_results_batch.assert_called()
        stored_result = mock_repo.store_analysis_results_batch.call_args[0][0][0]
        assert stored_result["outcome"] == "WIN"
        assert stored_result["intimation_id"] == 100

        # ---------------------------------------------------------
        # 4. Score
        # ---------------------------------------------------------
        # Setup repo to return unscored analysis
        mock_repo.get_unscored_analyses.return_value = [stored_result]
        mock_lawyer_repo.get_lawyer_ratings.return_value = [] # No existing ratings

        # Run Score
        await run_scoring(mock_repo, mock_lawyer_repo)

        # Verify
        mock_lawyer_repo.save_lawyer_ratings.assert_called()
        ratings = mock_lawyer_repo.save_lawyer_ratings.call_args[0][0]
        assert len(ratings) == 2  # Winner and Loser
        assert any(r["oab_number"] == "123" for r in ratings)
        mock_repo.mark_analyses_scored.assert_called()
