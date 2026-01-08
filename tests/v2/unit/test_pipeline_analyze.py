"""Unit tests for analysis pipeline."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from causaganha.analysis.models import DecisionAnalysis, Outcome
from causaganha.pipeline.analyze import run_analysis


@pytest.fixture
def mock_intimation_repo():
    return AsyncMock()

@pytest.fixture
def mock_analysis_repo():
    return AsyncMock()

@pytest.fixture
def mock_doc_service():
    return AsyncMock()

@pytest.fixture
def mock_analyzer():
    return AsyncMock()

@pytest.mark.asyncio
async def test_run_analysis_success(
    mock_intimation_repo,
    mock_analysis_repo,
    mock_doc_service,
    mock_analyzer,
):
    """Test successful analysis run."""
    # Setup Data
    mock_intimation_repo.get_unanalyzed_intimations.side_effect = [
        [{"id": 1, "link": "http://test.pdf"}],
        [], # Second call returns empty to stop loop
    ]

    mock_doc_service.download_pdf.return_value = b"PDF_CONTENT"

    analysis_result = DecisionAnalysis(
        outcome=Outcome.WIN,
        summary="Won",
        judge_name="Judge Dredd",
        confidence_score=0.9,
    )
    mock_analyzer.analyze_decision.return_value = analysis_result

    # Run
    await run_analysis(
        mock_intimation_repo,
        mock_analysis_repo,
        mock_doc_service,
        mock_analyzer,
        limit=1
    )

    # Verify
    mock_intimation_repo.get_unanalyzed_intimations.assert_called()
    mock_doc_service.download_pdf.assert_called_with("http://test.pdf")
    mock_analyzer.analyze_decision.assert_called_with(b"PDF_CONTENT")

    # Verify storage
    mock_analysis_repo.store_analysis_results_batch.assert_called_once()
    results = mock_analysis_repo.store_analysis_results_batch.call_args[0][0]
    assert len(results) == 1
    assert results[0]["intimation_id"] == 1
    assert results[0]["outcome"] == "WIN"

@pytest.mark.asyncio
async def test_run_analysis_download_fail(
    mock_intimation_repo,
    mock_analysis_repo,
    mock_doc_service,
    mock_analyzer,
):
    """Test analysis when download fails."""
    mock_intimation_repo.get_unanalyzed_intimations.side_effect = [
        [{"id": 1, "link": "http://test.pdf"}],
        [],
    ]

    mock_doc_service.download_pdf.return_value = None # Download failed

    await run_analysis(
        mock_intimation_repo,
        mock_analysis_repo,
        mock_doc_service,
        mock_analyzer,
        limit=1
    )

    mock_analyzer.analyze_decision.assert_not_called()

    # Should still store a result indicating failure
    mock_analysis_repo.store_analysis_results_batch.assert_called_once()
    results = mock_analysis_repo.store_analysis_results_batch.call_args[0][0]
    assert results[0]["outcome"] == "UNKNOWN"
    assert "Download failed" in results[0]["summary"]

@pytest.mark.asyncio
async def test_run_analysis_analyzer_fail(
    mock_intimation_repo,
    mock_analysis_repo,
    mock_doc_service,
    mock_analyzer,
):
    """Test analysis when analyzer raises exception."""
    mock_intimation_repo.get_unanalyzed_intimations.side_effect = [
        [{"id": 1, "link": "http://test.pdf"}],
        [],
    ]

    mock_doc_service.download_pdf.return_value = b"PDF"
    mock_analyzer.analyze_decision.side_effect = Exception("AI Error")

    await run_analysis(
        mock_intimation_repo,
        mock_analysis_repo,
        mock_doc_service,
        mock_analyzer,
        limit=1
    )

    # Should store failure
    mock_analysis_repo.store_analysis_results_batch.assert_called_once()
    results = mock_analysis_repo.store_analysis_results_batch.call_args[0][0]
    assert results[0]["outcome"] == "UNKNOWN"
    assert "Analysis failed: AI Error" in results[0]["summary"]

@pytest.mark.asyncio
async def test_run_analysis_missing_link(
    mock_intimation_repo,
    mock_analysis_repo,
    mock_doc_service,
    mock_analyzer,
):
    """Test skip item with missing link."""
    mock_intimation_repo.get_unanalyzed_intimations.side_effect = [
        [{"id": 1, "link": ""}],
        [],
    ]

    await run_analysis(
        mock_intimation_repo,
        mock_analysis_repo,
        mock_doc_service,
        mock_analyzer,
        limit=1
    )

    # Should not call download or analyze or store
    mock_doc_service.download_pdf.assert_not_called()
    mock_analysis_repo.store_analysis_results_batch.assert_not_called()

@pytest.mark.asyncio
async def test_run_analysis_empty_batch(
    mock_intimation_repo,
    mock_analysis_repo,
    mock_doc_service,
    mock_analyzer,
):
    """Test graceful exit if no items."""
    mock_intimation_repo.get_unanalyzed_intimations.return_value = []

    await run_analysis(
        mock_intimation_repo,
        mock_analysis_repo,
        mock_doc_service,
        mock_analyzer,
        limit=10
    )

    mock_doc_service.download_pdf.assert_not_called()
