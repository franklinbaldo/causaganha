"""End-to-end tests for the full lifecycle of CausaGanha V2."""

from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import pytest
from typer.testing import CliRunner

from causaganha.cli import app
from causaganha.v2.api.client import DestinarioAdvogado, Intimation, LawyerInfo
from causaganha.v2.storage.connection import get_connection

runner = CliRunner()


@pytest.fixture
def realistic_intimation_data() -> list[Intimation]:
    """Generate realistic intimation data mimicking PJe API response."""
    return [
        Intimation(
            id=1001,
            numero_processo="1234567-89.2024.8.22.0001",
            data_disponibilizacao="2024-12-15",
            siglaTribunal="TJRO",
            tipoComunicacao="Intimação",
            nomeOrgao="1ª Vara Cível de Porto Velho",
            texto="Intima-se a parte autora para manifestação sobre os documentos juntados.",
            link="https://pje.tjro.jus.br/docs/decisao_1001.pdf",
            tipoDocumento="PDF",
            nomeClasse="Procedimento Comum Cível",
            codigoClasse="318",
            hash="abc123def456",
            status="pending",
            destinatarioadvogados=[
                DestinarioAdvogado(
                    advogado=LawyerInfo(
                        id=1, nome="Dr. Teste", numero_oab="12345", uf_oab="RO"
                    )
                ),
                DestinarioAdvogado(
                    advogado=LawyerInfo(
                        id=2, nome="Dr. Oponente", numero_oab="67890", uf_oab="RO"
                    )
                ),
            ],
        ),
    ]


@pytest.fixture
def mock_llm_analysis() -> MagicMock:
    """Realistic LLM analysis response."""
    analysis = MagicMock()
    # Pydantic models usually aren't MagicMocks in the pipeline, but the analyzer returns objects.
    # The store_analysis function expects an object with attributes.
    analysis.outcome = "procedente"
    analysis.winner_lawyer_oab = "12345"
    analysis.winner_lawyer_state = "RO"
    analysis.winner_party_name = "Joao Autor"
    analysis.loser_lawyer_oab = "67890"
    analysis.loser_lawyer_state = "RO"
    analysis.loser_party_name = "Maria Re"
    analysis.decision_type = "sentença"
    analysis.decision_reasoning = "Presenca de todos os requisitos legais"
    analysis.judge_name = "Dr. Joao da Silva"
    analysis.confidence_score = 0.95
    return analysis


def test_full_lifecycle_e2e(
    tmp_path: Path,
    realistic_intimation_data: list[Intimation],
    mock_llm_analysis: MagicMock,
) -> None:
    """E2E Test ensuring the CLI pipeline command runs correctly from start to finish.

    Simulates: Collect -> Archive -> Analyze -> Score
    """
    db_path = tmp_path / "test_e2e.duckdb"

    # Mocks
    mock_client_instance = AsyncMock()
    mock_client_instance.get_intimations_by_court.return_value = (
        realistic_intimation_data
    )
    mock_client_instance.close = AsyncMock()

    mock_doc_service_instance = MagicMock()
    mock_doc_service_instance.download_pdf = AsyncMock(return_value=b"%PDF-1.4 Mock PDF")

    mock_archive_service_instance = AsyncMock()
    mock_archive_service_instance.upload_file.return_value = (
        "https://archive.org/details/mock_item"
    )
    mock_archive_service_instance.generate_metadata.return_value = {"title": "Test Item"}

    mock_analyzer_instance = AsyncMock()
    # The analyzer.analyze_batch returns a list of results
    mock_analyzer_instance.analyze_batch.return_value = [mock_llm_analysis]

    # Patch targets based on where they are INSTANTIATED or USED
    # 1. PJeAPIClient is instantiated inside causaganha.v2.pipeline.collect
    # 2. DecisionAnalyzer is instantiated inside causaganha.v2.pipeline.analyze
    # 3. DocumentService and create_archive_service are called in causaganha.cli

    # Also need to patch get_connection in cli and pipelines to ensure they all share the same DB
    # We can pass the path via config, but patching get_connection to return a connection to our temp DB is safer/easier

    con = get_connection(str(db_path))

    with patch(
        "causaganha.v2.pipeline.collect.PJeAPIClient",
        return_value=mock_client_instance,
    ), patch(
        "causaganha.cli.DocumentService", return_value=mock_doc_service_instance
    ), patch(
        "causaganha.cli.create_archive_service",
        return_value=mock_archive_service_instance,
    ), patch(
        "causaganha.v2.pipeline.analyze.DecisionAnalyzer",
        return_value=mock_analyzer_instance,
    ), patch(
        "causaganha.v2.storage.connection.get_connection", return_value=con
    ), patch(
        "causaganha.v2.pipeline.collect.get_connection", return_value=con
    ), patch(
        "causaganha.v2.pipeline.archive.get_connection", return_value=con
    ), patch(
        "causaganha.v2.pipeline.analyze.get_connection", return_value=con
    ), patch(
        "causaganha.cli.get_connection", return_value=con
    ):
        # 1. Initialize DB (Not strictly needed as get_connection auto-inits, but good to test CLI)
        result_init = runner.invoke(app, ["db", "init"])
        assert result_init.exit_code == 0

        # 2. Run Pipeline
        # We use --days-back 1 to keep it simple
        result_pipeline = runner.invoke(
            app,
            [
                "pipeline",
                "--courts",
                "TJRO",
                "--days-back",
                "1",
                "--analyze-limit",
                "10",
                "--archive-limit",
                "10",
                "--score-limit",
                "100",
            ],
        )

        assert result_pipeline.exit_code == 0
        assert "Step 1/4: Collecting intimations..." in result_pipeline.stdout
        assert "Step 2/4: Archiving to Internet Archive..." in result_pipeline.stdout
        assert "Step 3/4: Analyzing decisions..." in result_pipeline.stdout
        assert "Step 4/4: Calculating ratings..." in result_pipeline.stdout
        assert "Pipeline complete!" in result_pipeline.stdout

        # Verify DB state

        # Check intimations stored
        intimations = con.table("intimations").execute()
        assert len(intimations) == 1
        assert intimations["ia_url"].iloc[0] == "https://archive.org/details/mock_item"
        assert intimations["analyzed"].iloc[0]

        # Check analysis results
        analyses = con.table("decision_analysis").execute()
        assert len(analyses) == 1
        assert analyses["outcome"].iloc[0] == "procedente"
        assert analyses["winner_lawyer_oab"].iloc[0] == "12345"

        # Check ratings
        ratings = con.table("lawyer_ratings").execute()
        # We expect ratings because we had a winner (12345) and loser (67890)
        assert len(ratings) >= 2

        winner_rating = ratings[ratings["oab_number"] == "12345"].iloc[0]
        assert winner_rating["wins"] == 1

        loser_rating = ratings[ratings["oab_number"] == "67890"].iloc[0]
        assert loser_rating["losses"] == 1
