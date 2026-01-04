"""End-to-End lifecycle tests for CausaGanha V2."""

from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from causaganha.analysis.models import DecisionAnalysis, Outcome
from causaganha.cli import app
from causaganha.domain.models import Intimation
from causaganha.storage.connection import get_connection
from causaganha.storage.schema import create_schema


# Initialize runner
runner = CliRunner()

@pytest.fixture
def mock_db(tmp_path: Path) -> str:
    """Create a temporary DuckDB database for E2E testing."""
    db_path = tmp_path / "e2e_test.duckdb"
    con = get_connection(str(db_path))
    create_schema(con)
    return str(db_path)

@pytest.fixture
def mock_api_data() -> list[Intimation]:
    """Mock data returned by PJe API."""
    return [
        Intimation(
            id=5001,
            numero_processo="5001-89.2024.8.22.0001",
            data_disponibilizacao=date(2024, 12, 20),
            sigla_tribunal="TJRO",
            tipo_comunicacao="Intimação",
            nome_orgao="1ª Vara Cível",
            texto="Sentença: Julgo procedente.",
            link="https://pje.tjro.jus.br/docs/5001.pdf",
            tipo_documento="PDF",
            nome_classe="Procedimento Comum",
            codigo_classe="318",
            hash="hash5001",
            status="pending",
        ),
    ]

@pytest.fixture
def mock_analysis_result() -> MagicMock:
    """Mock result from DecisionAnalyzer."""
    analysis = MagicMock(spec=DecisionAnalysis)
    analysis.outcome = Outcome.WIN
    analysis.summary = "Victory for the plaintiff."
    analysis.judge_name = "Judge Dredd"
    analysis.confidence_score = 0.99
    analysis.winner_lawyer_oab = "12345"
    analysis.winner_lawyer_state = "RO"
    analysis.winner_party_name = "Winner"
    analysis.loser_lawyer_oab = "67890"
    analysis.loser_lawyer_state = "RO"
    analysis.loser_party_name = "Loser"
    analysis.decision_type = "Judgment"
    analysis.decision_reasoning = "Because I said so."
    return analysis

class TestFullLifecycle:
    """End-to-end tests for the full data lifecycle via CLI."""

    def test_pipeline_command_flow(
        self,
        mock_db: str,
        mock_api_data: list[Intimation],
        mock_analysis_result: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify the 'pipeline' command executes all stages: Collect -> Archive -> Analyze -> Score."""
        # Patch the database path in config/cli
        # Since DB_PATH is imported in cli.py, we need to patch where it's used or how connection is made.
        # In cli.py: con = get_connection(DB_PATH).
        # We can patch 'causaganha.cli.DB_PATH' if it is imported there, or patch 'causaganha.cli.get_connection'.

        # Patching get_connection to return connection to our tmp db
        original_get_connection = get_connection
        def mock_get_conn(path: str | None = None) -> object:
            return original_get_connection(mock_db)

        monkeypatch.setattr("causaganha.cli.get_connection", mock_get_conn)
        # Note: pipeline modules do not use get_connection directly, they receive repository from CLI.

        # NOTE: The CLI uses a helper `_get_repository` which calls `get_connection(DB_PATH)`.
        # So patching `causaganha.cli.get_connection` should work if we ensure `DB_PATH` arg is ignored or handled.
        # But `_get_repository` calls `get_connection(DB_PATH)`.
        # If we patch `causaganha.cli.get_connection`, our mock needs to accept the argument but ignore it
        # (or we just rely on `mock_get_conn` which ignores `path` arg and uses `mock_db`).

        # Mock PJeAPIClient
        with patch("causaganha.cli.PJeAPIClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get_intimations_by_court.return_value = mock_api_data
            MockClient.return_value = mock_client_instance

            # Mock DocumentService and InternetArchiveService
            with patch("causaganha.cli.DocumentService") as MockDocService, \
                 patch("causaganha.cli.create_archive_service") as MockCreateArchiveService, \
                 patch("causaganha.pipeline.archive.DocumentService") as MockPipeDocService, \
                 patch("causaganha.pipeline.analyze.DocumentService") as MockPipeAnalyzeDocService:

                # Setup Document Service
                mock_doc_service = AsyncMock()
                mock_doc_service.download_pdf.return_value = b"PDF CONTENT"
                MockDocService.return_value = mock_doc_service
                MockPipeDocService.return_value = mock_doc_service
                MockPipeAnalyzeDocService.return_value = mock_doc_service

                # Setup Archive Service
                mock_archive_service = AsyncMock()
                mock_archive_service.upload_file.return_value = "https://archive.org/details/test_item"
                MockCreateArchiveService.return_value = mock_archive_service

                # Mock DecisionAnalyzer
                with patch("causaganha.cli.DecisionAnalyzer") as MockAnalyzer, \
                     patch("causaganha.pipeline.analyze.DecisionAnalyzer") as MockPipeAnalyzer:

                    mock_analyzer = AsyncMock()
                    mock_analyzer.analyze_decision.return_value = mock_analysis_result
                    MockAnalyzer.return_value = mock_analyzer
                    MockPipeAnalyzer.return_value = mock_analyzer

                    # Execute the CLI command
                    result = runner.invoke(app, [
                        "pipeline",
                        "--start-date", "2024-12-20",
                        "--end-date", "2024-12-20",
                        "--courts", "TJRO",
                        "--analyze-limit", "1",
                        "--score-limit", "1",
                        "--archive-limit", "1",
                    ])

        # Verify CLI success
        assert result.exit_code == 0, f"CLI command failed with output: {result.stdout}"
        assert "Pipeline complete!" in result.stdout

        # Verify Database State
        con = get_connection(mock_db)

        # 1. Check Intimations (Collection)
        intimations = con.table("intimations").execute()
        assert len(intimations) == 1
        assert intimations.iloc[0]["numero_processo"] == "5001-89.2024.8.22.0001"

        # 2. Check Archive (Archive)
        # Note: Depending on async execution order and batching, verify fields are updated.
        # The pipeline runs sequentially: Collect -> Archive -> Analyze -> Score.
        # So IA URL should be present.
        assert intimations.iloc[0]["ia_url"] == "https://archive.org/details/test_item"

        # 3. Check Analysis Results (Analyze)
        analysis_results = con.table("analysis_results").execute()
        assert len(analysis_results) == 1
        assert analysis_results.iloc[0]["outcome"] == "WIN"

        # 4. Check Ratings (Score)
        ratings = con.table("lawyer_ratings").execute()
        assert len(ratings) >= 2 # Winner and Loser
        winner = ratings[ratings["oab_number"] == "12345"]
        assert len(winner) == 1
        assert winner.iloc[0]["wins"] == 1
