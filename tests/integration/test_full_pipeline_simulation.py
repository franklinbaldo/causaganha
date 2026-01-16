"""Integration test simulating full pipeline with realistic data (TDD)."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse

import pytest

from causaganha.application.pipeline.analyze import run_analysis
from causaganha.application.pipeline.archive import run_archive
from causaganha.application.pipeline.collect import run_collection
from causaganha.application.pipeline.score import run_scoring
from causaganha.domain.models import Intimation
from causaganha.infrastructure.clients.archive import InternetArchiveService
from causaganha.infrastructure.clients.document import DocumentService
from causaganha.infrastructure.integrations.pje.client import PJeAPIClient
from causaganha.infrastructure.storage.connection import get_connection
from causaganha.infrastructure.storage.repositories.intimation import IntimationRepository
from causaganha.infrastructure.storage.schema import create_schema


@pytest.fixture
def test_db(tmp_path):
    """Create a test database with schema."""
    db_path = tmp_path / "test_pipeline.duckdb"
    con = get_connection(str(db_path))
    create_schema(con)
    yield str(db_path), con
    con.con.close()


@pytest.fixture
def repository(test_db):
    """Create repository with test database."""
    _, con = test_db
    return IntimationRepository(con)


@pytest.fixture
def realistic_intimation_data():
    """Generate realistic intimation data mimicking PJe API response."""
    return [
        Intimation(
            id=1001,
            numero_processo="1234567-89.2024.8.22.0001",
            data_disponibilizacao=datetime(2024, 12, 15),
            sigla_tribunal="TJRO",
            tipo_comunicacao="Intimação",
            nome_orgao="1ª Vara Cível de Porto Velho",
            texto="Intima-se a parte autora para manifestação sobre os documentos juntados pela parte ré.",
            link="https://pje.tjro.jus.br/docs/decisao_1001.pdf",
            tipo_documento="PDF",
            nome_classe="Procedimento Comum Cível",
            codigo_classe="318",
            hash="abc123def456",
            status="pending",
        ),
        Intimation(
            id=1002,
            numero_processo="9876543-21.2024.8.22.0002",
            data_disponibilizacao=datetime(2024, 12, 15),
            sigla_tribunal="TJRO",
            tipo_comunicacao="Intimação",
            nome_orgao="2ª Vara Cível de Porto Velho",
            texto="Intima-se as partes para audiência de conciliação.",
            link="https://pje.tjro.jus.br/docs/decisao_1002.pdf",
            tipo_documento="PDF",
            nome_classe="Procedimento Comum Cível",
            codigo_classe="318",
            hash="xyz789uvw123",
            status="pending",
        ),
    ]


@pytest.fixture
def mock_pdf_content() -> bytes:
    """Realistic PDF content (as bytes)."""
    return b"%PDF-1.4\n%Mock PDF content for testing\nSentenca: Julgo procedente o pedido.\nAdvogado: Dr. Joao Silva, OAB/RO 12345"


@pytest.fixture
def mock_llm_analysis():
    """Realistic LLM analysis response as Pydantic-like object."""
    # Create mock object that matches DecisionAnalysis structure
    analysis = MagicMock()
    analysis.outcome = MagicMock()
    analysis.outcome.value = "favorable"
    analysis.summary = "Pedido julgado procedente em favor do autor"
    analysis.judge_name = "Dr. Joao da Silva"
    analysis.confidence_score = 0.95
    analysis.winner_lawyer_oab = "12345"
    analysis.winner_lawyer_state = "RO"
    analysis.winner_party_name = "Joao Autor"
    analysis.loser_lawyer_oab = "67890"
    analysis.loser_lawyer_state = "RO"
    analysis.loser_party_name = "Maria Re"
    analysis.decision_type = "Sentenca"
    analysis.decision_reasoning = "Presenca de todos os requisitos legais"
    return analysis


class TestFullPipelineSimulation:
    """Test complete pipeline workflow with realistic simulated data (TDD)."""

    @pytest.mark.asyncio
    async def test_complete_pipeline_collect_to_score(
        self,
        repository,
        test_db,
        realistic_intimation_data,
        mock_pdf_content,
        mock_llm_analysis,
        tmp_path,
    ) -> None:
        """Simulate complete real-world workflow:
        1. Collect intimations from PJe API
        2. Archive PDFs to Internet Archive
        3. Analyze decisions with LLM
        4. Calculate lawyer ratings.

        This test verifies all components work together end-to-end.
        """
        _db_path, con = test_db

        # ==========================================
        # STEP 1: COLLECT - Simulate PJe API
        # ==========================================
        with patch.object(
            PJeAPIClient, "get_intimations_by_court", new_callable=AsyncMock
        ) as mock_api:
            mock_api.return_value = realistic_intimation_data

            client = PJeAPIClient()

            # Run collection
            await run_collection(
                repository,
                client,
                start_date="2024-12-15",
                end_date="2024-12-15",
                courts=["TJRO"],
            )

            await client.close()

        # Verify intimations were stored
        all_intimations = con.table("intimations").execute()
        assert len(all_intimations) == 2, "Should have stored 2 intimations"
        assert all_intimations["numero_processo"].tolist() == [
            "1234567-89.2024.8.22.0001",
            "9876543-21.2024.8.22.0002",
        ]

        # ==========================================
        # STEP 2: ARCHIVE - Simulate IA Upload
        # ==========================================
        with (
            patch.object(DocumentService, "download_pdf", new_callable=AsyncMock) as mock_download,
            patch.object(
                InternetArchiveService, "upload_file", new_callable=AsyncMock
            ) as mock_upload,
        ):
            # Mock PDF download
            mock_download.return_value = mock_pdf_content

            # Mock IA upload (return realistic IA URL)
            def mock_ia_upload(file_path, item_id, metadata) -> str:
                return f"https://archive.org/details/{item_id}"

            mock_upload.side_effect = mock_ia_upload

            doc_service = DocumentService()
            ia_service = InternetArchiveService()

            # Run archive
            await run_archive(
                repository,
                doc_service,
                ia_service,
                limit=10,
                dry_run=False,
            )

        # Verify intimations were archived
        archived = (
            con.table("intimations")
            .filter(
                con.table("intimations").ia_url.notnull(),
            )
            .execute()
        )

        assert len(archived) == 2, "Should have archived both intimations"
        assert all(urlparse(url).hostname == "archive.org" for url in archived["ia_url"].tolist())
        assert archived["archived_at"].notnull().all(), "All should have archive timestamp"

        # Verify they don't appear in unarchived anymore
        unarchived = await repository.get_unarchived_intimations(limit=10)
        assert len(unarchived) == 0, "No intimations should be unarchived"

        # ==========================================
        # STEP 3: ANALYZE - Simulate LLM Analysis
        # ==========================================
        # Mock the entire analysis call to avoid needing API keys
        with patch("causaganha.application.pipeline.analyze.DecisionAnalyzer") as MockAnalyzer:
            mock_analyzer_instance = AsyncMock()
            mock_analyzer_instance.analyze_decision.return_value = mock_llm_analysis
            MockAnalyzer.return_value = mock_analyzer_instance

            with patch.object(
                DocumentService, "download_pdf", new_callable=AsyncMock
            ) as mock_download:
                mock_download.return_value = mock_pdf_content

                doc_service = DocumentService()
                analyzer = MockAnalyzer()

                # Run analysis
                from causaganha.infrastructure.storage.repositories.analysis import (
                    AnalysisRepository,
                )

                analysis_repo = AnalysisRepository(con)
                await run_analysis(
                    repository,
                    analysis_repo,
                    doc_service,
                    analyzer,
                    limit=10,
                )

        # Verify analyses were stored
        analyses = con.table("analysis_results").execute()
        assert len(analyses) == 2, "Should have 2 analysis results"
        assert analyses["outcome"].tolist() == ["favorable", "favorable"]
        assert all(score > 0.9 for score in analyses["confidence_score"].tolist())

        # ==========================================
        # STEP 4: SCORE - Calculate Ratings
        # ==========================================
        # Run scoring
        from causaganha.infrastructure.storage.repositories.lawyer import LawyerRatingRepository

        rating_repo = LawyerRatingRepository(con)
        await run_scoring(analysis_repo, rating_repo, limit=100)

        # Verify ratings were calculated
        ratings = con.table("lawyer_ratings").execute()
        assert len(ratings) > 0, "Should have calculated lawyer ratings"

        # Verify lawyer stats
        winner_lawyer = ratings[ratings["oab_number"] == "12345"]
        assert len(winner_lawyer) == 1
        assert winner_lawyer["wins"].iloc[0] == 2, "Winner should have 2 wins"

        loser_lawyer = ratings[ratings["oab_number"] == "67890"]
        assert len(loser_lawyer) == 1
        assert loser_lawyer["losses"].iloc[0] == 2, "Loser should have 2 losses"

        # Verify analyses marked as scored
        scored_analyses = (
            con.table("analysis_results")
            .filter(
                con.table("analysis_results").scored,
            )
            .execute()
        )
        assert len(scored_analyses) == 2, "Both analyses should be marked as scored"

    @pytest.mark.asyncio
    async def test_pipeline_handles_missing_links(
        self,
        repository,
        test_db,
        mock_pdf_content,
    ) -> None:
        """Test that pipeline gracefully handles intimations without download links."""
        _db_path, con = test_db

        # Create intimation without link
        intimation_no_link = Intimation(
            id=2001,
            numero_processo="5555555-55.2024.8.22.0001",
            data_disponibilizacao=datetime(2024, 12, 15),
            sigla_tribunal="TJRO",
            tipo_comunicacao="Intimação",
            nome_orgao="3ª Vara Cível",
            texto="Test without link",
            link=None,  # No download link
            tipo_documento="PDF",
            nome_classe="Comum",
            codigo_classe="318",
            hash="nolink123",
            status="pending",
        )

        # Store it
        await repository.store_intimations([intimation_no_link])

        # Try to archive - should skip this one
        with (
            patch.object(DocumentService, "download_pdf", new_callable=AsyncMock) as mock_download,
            patch.object(
                InternetArchiveService, "upload_file", new_callable=AsyncMock
            ) as mock_upload,
        ):
            mock_download.return_value = mock_pdf_content
            mock_upload.return_value = "https://archive.org/details/test"

            doc_service = DocumentService()
            ia_service = InternetArchiveService()

            # Should not crash, just skip
            await run_archive(repository, doc_service, ia_service, limit=10, dry_run=False)

        # Verify it wasn't archived (no link to download)
        result = (
            con.table("intimations")
            .filter(
                con.table("intimations").id == 2001,
            )
            .execute()
        )

        assert result["ia_url"].iloc[0] is None or result["ia_url"].isna().iloc[0], (
            "Intimation without link should not be archived"
        )

    @pytest.mark.asyncio
    async def test_pipeline_dry_run_mode(
        self,
        repository,
        realistic_intimation_data,
        mock_pdf_content,
    ) -> None:
        """Test that dry-run mode doesn't actually archive anything."""
        # Store intimations
        await repository.store_intimations(realistic_intimation_data)

        with (
            patch.object(DocumentService, "download_pdf", new_callable=AsyncMock) as mock_download,
            patch.object(
                InternetArchiveService, "upload_file", new_callable=AsyncMock
            ) as mock_upload,
        ):
            mock_download.return_value = mock_pdf_content

            doc_service = DocumentService()
            ia_service = InternetArchiveService()

            # Run in dry-run mode
            await run_archive(repository, doc_service, ia_service, limit=10, dry_run=True)

        # Verify IA upload was NOT called (dry run)
        mock_upload.assert_not_called()

        # Verify intimations are still unarchived
        unarchived = await repository.get_unarchived_intimations(limit=10)
        assert len(unarchived) == 2, "Intimations should still be unarchived in dry-run mode"

    @pytest.mark.asyncio
    async def test_pipeline_respects_limits(
        self,
        repository,
        test_db,
    ) -> None:
        """Test that pipeline operations respect limit parameters."""
        _, con = test_db

        # Create 10 intimations
        intimations = [
            Intimation(
                id=3000 + i,
                numero_processo=f"{7000000 + i}-89.2024.8.22.0001",
                data_disponibilizacao=datetime(2024, 12, 15),
                sigla_tribunal="TJRO",
                tipo_comunicacao="Intimação",
                nome_orgao="Vara Teste",
                texto=f"Test {i}",
                link=f"https://example.com/{i}.pdf",
                tipo_documento="PDF",
                nome_classe="Comum",
                codigo_classe="318",
                hash=f"hash{i}",
                status="pending",
            )
            for i in range(10)
        ]

        await repository.store_intimations(intimations)

        # Get only 3 unarchived
        unarchived = await repository.get_unarchived_intimations(limit=3)
        assert len(unarchived) == 3, "Should respect limit of 3"

        # Archive only 5
        with (
            patch.object(DocumentService, "download_pdf", new_callable=AsyncMock) as mock_download,
            patch.object(
                InternetArchiveService, "upload_file", new_callable=AsyncMock
            ) as mock_upload,
        ):
            mock_download.return_value = b"fake pdf"
            mock_upload.return_value = "https://archive.org/details/test"

            doc_service = DocumentService()
            ia_service = InternetArchiveService()

            await run_archive(repository, doc_service, ia_service, limit=5, dry_run=False)

        # Verify only 5 were archived
        archived = (
            con.table("intimations")
            .filter(
                con.table("intimations").ia_url.notnull(),
            )
            .execute()
        )
        assert len(archived) == 5, "Should have archived exactly 5"

        # Verify 5 remain unarchived
        unarchived_after = await repository.get_unarchived_intimations(limit=100)
        assert len(unarchived_after) == 5, "Should have 5 unarchived remaining"
