from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from causaganha.cli import app
from causaganha.domain.models import Intimation
from causaganha.infrastructure.storage.connection import get_connection


runner = CliRunner()


@pytest.fixture
def realistic_intimation_data() -> list[Intimation]:
    """Generate realistic intimation data mimicking PJe API response."""
    return [
        Intimation(
            id=1001,
            numero_processo="1234567-89.2024.8.22.0001",
            data_disponibilizacao=datetime(
                2024,
                12,
                15,
                tzinfo=UTC,
            ),  # type: ignore[arg-type]
            sigla_tribunal="TJRO",
            tipo_comunicacao="Intimação",
            nome_orgao="1ª Vara Cível de Porto Velho",
            texto="Intima-se a parte autora para manifestação sobre os documentos juntados.",
            link="https://pje.tjro.jus.br/docs/decisao_1001.pdf",
            tipo_documento="PDF",
            nome_classe="Procedimento Comum Cível",
            codigo_classe="318",
            hash="abc123def456",
            status="pending",
            meio="Diário da Justiça",
            ativo=True,
            meiocompleto="Diário da Justiça Eletrônico",
            datadisponibilizacao="2024-12-15 00:00:00",
        ),
    ]


@pytest.fixture
def mock_llm_analysis() -> MagicMock:
    """Realistic LLM analysis response."""
    analysis = MagicMock()
    analysis.outcome.value = "WIN"
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


def test_full_lifecycle_e2e(
    tmp_path: pytest.TempPathFactory,
    realistic_intimation_data: list[Intimation],
    mock_llm_analysis: MagicMock,
) -> None:
    """E2E Test ensuring the CLI pipeline command runs correctly from start to finish.

    Simulates: Collect -> Archive -> Analyze -> Score
    """
    db_path = tmp_path / "test_e2e.duckdb"

    # Mocks
    mock_client_instance = AsyncMock()
    mock_client_instance.get_intimations_by_court.return_value = realistic_intimation_data

    mock_doc_service_instance = MagicMock()
    # Ensure download_pdf is async mock if called with await
    mock_doc_service_instance.download_pdf = AsyncMock(return_value=b"%PDF-1.4 Mock PDF")

    mock_archive_service_instance = AsyncMock()
    mock_archive_service_instance.upload_file.return_value = "https://archive.org/details/mock_item"

    mock_analyzer_instance = AsyncMock()
    mock_analyzer_instance.analyze_decision.return_value = mock_llm_analysis

    # We need to patch the classes/factories in causaganha.cli
    with (
        patch("causaganha.cli.DB_PATH", str(db_path)),
        patch("causaganha.cli.PJeAPIClient", return_value=mock_client_instance),
        patch("causaganha.cli.DocumentService", return_value=mock_doc_service_instance),
        patch(
            "causaganha.cli.create_archive_service",
            return_value=mock_archive_service_instance,
        ),
        patch("causaganha.cli.DecisionAnalyzer", return_value=mock_analyzer_instance),
    ):
        # 1. Initialize DB
        result_init = runner.invoke(app, ["db", "init"])
        assert result_init.exit_code == 0
        assert "Schema created successfully" in result_init.stdout

        # 2. Run Pipeline
        # We use --skip-collect=False implicitly
        result_pipeline = runner.invoke(app, ["pipeline", "--courts", "TJRO"])

        assert result_pipeline.exit_code == 0
        assert "Step 1/4: Collecting intimations..." in result_pipeline.stdout
        assert "Step 2/4: Archiving to Internet Archive..." in result_pipeline.stdout
        assert "Step 3/4: Analyzing decisions..." in result_pipeline.stdout
        assert "Step 4/4: Calculating ratings..." in result_pipeline.stdout
        assert "Pipeline complete!" in result_pipeline.stdout

        # Verify DB state - we can inspect the DB file to be sure
        con = get_connection(str(db_path))

        # Check intimations
        intimations = con.table("intimations").execute()
        assert len(intimations) == 1
        assert intimations["ia_url"].iloc[0] == "https://archive.org/details/mock_item"

        # Check analysis
        analyses = con.table("analysis_results").execute()
        assert len(analyses) == 1
        assert analyses["outcome"].iloc[0] == "WIN"

        # Check ratings
        ratings = con.table("lawyer_ratings").execute()
        # We expect ratings because we had a winner and loser
        assert len(ratings) > 0
