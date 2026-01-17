from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from causaganha.cli import app
from causaganha.v2.api.client import Intimation, DestinarioAdvogado, LawyerInfo
from causaganha.v2.storage.connection import get_connection
from causaganha.v2.analysis.models import DecisionAnalysis


runner = CliRunner()


@pytest.fixture
def realistic_intimation_data() -> list[Intimation]:
    """Generate realistic intimation data mimicking PJe API response."""
    return [
        Intimation(
            id=1001,
            siglaTribunal="TJRO",
            numero_processo="1234567-89.2024.8.22.0001",
            data_disponibilizacao="2024-12-15",
            tipoComunicacao="Intimação",
            nomeOrgao="1ª Vara Cível de Porto Velho",
            texto="Intima-se a parte autora para manifestação sobre os documentos juntados.",
            link="https://pje.tjro.jus.br/docs/decisao_1001.pdf",
            tipoDocumento="PDF",
            nomeClasse="Procedimento Comum Cível",
            codigoClasse="318",
            hash="abc123def456",
            status="P",
            destinatarioadvogados=[
                DestinarioAdvogado(
                    advogado=LawyerInfo(
                        id=1,
                        nome="Advogado Teste",
                        numero_oab="12345",
                        uf_oab="RO"
                    )
                )
            ]
        ),
    ]


@pytest.fixture
def mock_llm_analysis() -> list[DecisionAnalysis]:
    """Realistic LLM analysis response."""
    analysis = DecisionAnalysis(
        winner_lawyer_oab="12345",
        winner_lawyer_state="RO",
        winner_party_name="Joao Autor",
        loser_lawyer_oab="67890",
        loser_lawyer_state="RO",
        loser_party_name="Maria Re",
        decision_type="Sentença",
        outcome="procedente",
        judge_name="Dr. Joao da Silva",
        decision_reasoning="Presenca de todos os requisitos legais",
        confidence_score=0.95
    )
    return [analysis]


def test_full_lifecycle_e2e(
    tmp_path: pytest.TempPathFactory,
    realistic_intimation_data: list[Intimation],
    mock_llm_analysis: list[DecisionAnalysis],
) -> None:
    """E2E Test ensuring the CLI pipeline command runs correctly from start to finish.

    Simulates: Collect -> Archive -> Analyze -> Score
    """
    db_path = tmp_path / "test_e2e.duckdb"

    # Mocks
    mock_client_instance = AsyncMock()
    mock_client_instance.get_intimations_by_court.return_value = realistic_intimation_data

    mock_doc_service_instance = MagicMock()
    mock_doc_service_instance.download_pdf = AsyncMock(return_value=b"%PDF-1.4 Mock PDF")

    mock_archive_service_instance = MagicMock()
    mock_archive_service_instance.generate_metadata.return_value = {"title": "Test"}

    mock_preservation_instance = AsyncMock()
    mock_preservation_instance.preserve_document.return_value = "https://archive.org/details/mock_item"

    mock_analyzer_instance = AsyncMock()
    mock_analyzer_instance.analyze_batch.return_value = mock_llm_analysis

    # We need to patch where they are used.
    # In V2, 'PJeAPIClient' is instantiated inside 'collect_metadata_for_court' in 'causaganha.v2.pipeline.collect'
    # 'DocumentService' is instantiated inside CLI
    # 'DecisionAnalyzer' is instantiated inside 'analyze_pending_decisions'

    with (
        patch("causaganha.v2.pipeline.collect.PJeAPIClient", return_value=mock_client_instance),
        patch("causaganha.v2.storage.connection.get_connection", side_effect=lambda: get_connection(str(db_path))),
        patch("causaganha.cli.DocumentService", return_value=mock_doc_service_instance),
        patch("causaganha.cli.create_archive_service", return_value=mock_archive_service_instance),
        patch("causaganha.v2.pipeline.archive.PreservationService", return_value=mock_preservation_instance),
        patch("causaganha.v2.pipeline.analyze.DecisionAnalyzer", return_value=mock_analyzer_instance),
    ):
        # 1. Initialize DB (Optional as V2 auto-inits, but good for testing CLI)
        result_init = runner.invoke(app, ["db", "init"])
        assert result_init.exit_code == 0
        assert "Schema initialized successfully" in result_init.stdout

        # 2. Run Pipeline
        # We also need to force schema re-creation if the DB file is new in the mock context
        # But get_connection handles it.

        # Ensure we don't have lingering state in singleton
        import causaganha.v2.storage.connection
        causaganha.v2.storage.connection._connection = None

        result_pipeline = runner.invoke(app, ["pipeline", "--courts", "TJRO"])

        if result_pipeline.exit_code != 0:
            print(result_pipeline.stdout)

        assert result_pipeline.exit_code == 0
        assert "Step 1/4: Collecting intimations..." in result_pipeline.stdout
        assert "Step 2/4: Archiving to Internet Archive..." in result_pipeline.stdout
        assert "Step 3/4: Analyzing decisions..." in result_pipeline.stdout
        assert "Step 4/4: Calculating ratings..." in result_pipeline.stdout
        assert "Pipeline complete!" in result_pipeline.stdout

        # Verify DB state
        con = get_connection(str(db_path))

        # Check intimations
        intimations = con.table("intimations").execute()
        assert len(intimations) == 1
        assert intimations["ia_url"].iloc[0] == "https://archive.org/details/mock_item"

        # Check analysis
        analyses = con.table("decision_analysis").execute()
        assert len(analyses) == 1
        assert analyses["outcome"].iloc[0] == "procedente"

        # Check ratings
        ratings = con.table("lawyer_ratings").execute()
        # We expect ratings because we had a winner and loser
        assert len(ratings) > 0

        # Verify specific rating update (Winner)
        winner_rating = ratings[ratings['oab_number'] == '12345'].iloc[0]
        assert winner_rating['wins'] == 1
