import pytest
from unittest.mock import AsyncMock, patch
from datetime import date
from causaganha.pipeline.analyze import run_analysis
from causaganha.domain.models import Intimation
from causaganha.analysis.models import DecisionAnalysis, Outcome
from causaganha.storage.repositories.intimation import IntimationRepository
from causaganha.storage.repositories.analysis import AnalysisRepository
from causaganha.services.document import DocumentService
from causaganha.analysis.analyzer import DecisionAnalyzer

@pytest.fixture
def mock_intimation_repo():
    return AsyncMock(spec=IntimationRepository)

@pytest.fixture
def mock_analysis_repo():
    return AsyncMock(spec=AnalysisRepository)

@pytest.fixture
def mock_doc_service():
    return AsyncMock(spec=DocumentService)

@pytest.fixture
def mock_analyzer():
    return AsyncMock(spec=DecisionAnalyzer)

@pytest.mark.asyncio
async def test_run_analysis_success(
    mock_intimation_repo,
    mock_analysis_repo,
    mock_doc_service,
    mock_analyzer
):
    # Setup
    intimation = Intimation(
        id=1,
        link="http://example.com/doc.pdf",
        numero_processo="123",
        sigla_tribunal="TJRO",
        data_disponibilizacao=date(2023, 1, 1),
        tipo_comunicacao="Intimação",
        nome_orgao="Vara Cível",
        texto="Texto",
        tipo_documento="Decisão",
        nome_classe="Procedimento Comum",
        hash="abc",
        status="A",
        advogados=[],
        partes=[]
    )
    mock_intimation_repo.get_unanalyzed_intimations.side_effect = [[intimation], []]

    mock_doc_service.download_pdf.return_value = b"pdf content"

    analysis_result = DecisionAnalysis(
        outcome=Outcome.WIN,
        summary="Summary",
        winner_lawyer_oab="123",
        winner_lawyer_state="RO",
        winner_party_name="Winner",
        loser_lawyer_oab="456",
        loser_lawyer_state="RO",
        loser_party_name="Loser",
        decision_type="Sentença",
        judge_name="Judge",
        decision_reasoning="Reasoning",
        confidence_score=0.9
    )
    mock_analyzer.analyze_decision.return_value = analysis_result

    # Execute
    await run_analysis(
        mock_intimation_repo,
        mock_analysis_repo,
        mock_doc_service,
        mock_analyzer,
        limit=1
    )

    # Verify
    mock_intimation_repo.get_unanalyzed_intimations.assert_called()
    mock_doc_service.download_pdf.assert_called_with("http://example.com/doc.pdf")
    mock_analyzer.analyze_decision.assert_called_with(b"pdf content")
    mock_analysis_repo.store_analysis_results_batch.assert_called_once()

    # Check stored result
    stored_batch = mock_analysis_repo.store_analysis_results_batch.call_args[0][0]
    assert len(stored_batch) == 1
    assert stored_batch[0]["intimation_id"] == 1
    assert stored_batch[0]["outcome"] == Outcome.WIN

@pytest.mark.asyncio
async def test_run_analysis_download_failed(
    mock_intimation_repo,
    mock_analysis_repo,
    mock_doc_service,
    mock_analyzer
):
    # Setup
    intimation = Intimation(
        id=1,
        link="http://example.com/doc.pdf",
        numero_processo="123",
        sigla_tribunal="TJRO",
        data_disponibilizacao=date(2023, 1, 1),
        tipo_comunicacao="Intimação",
        nome_orgao="Vara Cível",
        texto="Texto",
        tipo_documento="Decisão",
        nome_classe="Procedimento Comum",
        hash="abc",
        status="A"
    )
    mock_intimation_repo.get_unanalyzed_intimations.side_effect = [[intimation], []]
    mock_doc_service.download_pdf.return_value = None

    # Execute
    await run_analysis(
        mock_intimation_repo,
        mock_analysis_repo,
        mock_doc_service,
        mock_analyzer,
        limit=1
    )

    # Verify
    mock_doc_service.download_pdf.assert_called()
    mock_analyzer.analyze_decision.assert_not_called()
    mock_analysis_repo.store_analysis_results_batch.assert_called_once()

    stored_batch = mock_analysis_repo.store_analysis_results_batch.call_args[0][0]
    assert len(stored_batch) == 1
    assert "Download failed" in stored_batch[0]["summary"]

@pytest.mark.asyncio
async def test_run_analysis_missing_link(
    mock_intimation_repo,
    mock_analysis_repo,
    mock_doc_service,
    mock_analyzer
):
    # Setup
    intimation = Intimation(
        id=1,
        link=None, # Missing link
        numero_processo="123",
        sigla_tribunal="TJRO",
        data_disponibilizacao=date(2023, 1, 1),
        tipo_comunicacao="Intimação",
        nome_orgao="Vara Cível",
        texto="Texto",
        tipo_documento="Decisão",
        nome_classe="Procedimento Comum",
        hash="abc",
        status="A"
    )
    mock_intimation_repo.get_unanalyzed_intimations.side_effect = [[intimation], []]

    # Execute
    await run_analysis(
        mock_intimation_repo,
        mock_analysis_repo,
        mock_doc_service,
        mock_analyzer,
        limit=1
    )

    # Verify
    mock_doc_service.download_pdf.assert_not_called()
    mock_analysis_repo.store_analysis_results_batch.assert_not_called()

@pytest.mark.asyncio
async def test_run_analysis_exception(
    mock_intimation_repo,
    mock_analysis_repo,
    mock_doc_service,
    mock_analyzer
):
    # Setup
    intimation = Intimation(
        id=1,
        link="http://example.com/doc.pdf",
        numero_processo="123",
        sigla_tribunal="TJRO",
        data_disponibilizacao=date(2023, 1, 1),
        tipo_comunicacao="Intimação",
        nome_orgao="Vara Cível",
        texto="Texto",
        tipo_documento="Decisão",
        nome_classe="Procedimento Comum",
        hash="abc",
        status="A"
    )
    mock_intimation_repo.get_unanalyzed_intimations.side_effect = [[intimation], []]
    mock_doc_service.download_pdf.return_value = b"pdf content"
    mock_analyzer.analyze_decision.side_effect = Exception("Analysis Error")

    # Execute
    await run_analysis(
        mock_intimation_repo,
        mock_analysis_repo,
        mock_doc_service,
        mock_analyzer,
        limit=1
    )

    # Verify
    mock_analysis_repo.store_analysis_results_batch.assert_called_once()
    stored_batch = mock_analysis_repo.store_analysis_results_batch.call_args[0][0]
    assert len(stored_batch) == 1
    assert "Analysis Error" in stored_batch[0]["summary"]
