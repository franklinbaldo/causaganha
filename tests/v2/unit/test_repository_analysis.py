"""Unit tests for AnalysisRepository."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from ibis import BaseBackend

from causaganha.storage.repositories.analysis import AnalysisRepository


@pytest.fixture
def mock_con():
    """Mock Ibis connection."""
    con = MagicMock(spec=BaseBackend)
    con.con = MagicMock() # Mock the raw connection (DuckDB)
    # Ensure 'insert' is mocked
    con.insert = MagicMock()
    return con

@pytest.fixture
def analysis_repo(mock_con):
    """AnalysisRepository instance."""
    return AnalysisRepository(mock_con)

@pytest.mark.asyncio
async def test_store_analysis_result(analysis_repo, mock_con):
    """Test storing a single analysis result."""
    result = {
        "intimation_id": 123,
        "analyzed_at": datetime.now(UTC),
        "outcome": "WIN",
    }

    await analysis_repo.store_analysis_result(result)

    # Verify ibis.memtable and insert were called
    mock_con.insert.assert_called_once()
    assert mock_con.insert.call_args[0][0] == "analysis_results"

    # Verify update on raw connection
    mock_con.con.execute.assert_called_once()
    sql = mock_con.con.execute.call_args[0][0]
    assert "UPDATE intimations" in sql
    assert "WHERE id = ?" in sql

@pytest.mark.asyncio
async def test_store_analysis_results_batch(analysis_repo, mock_con):
    """Test batch storage."""
    results = [
        {"intimation_id": 1, "outcome": "WIN"},
        {"intimation_id": 2, "outcome": "LOSS"},
    ]

    await analysis_repo.store_analysis_results_batch(results)

    mock_con.insert.assert_called_once()

    # Verify update
    mock_con.con.execute.assert_called_once()
    sql = mock_con.con.execute.call_args[0][0]
    assert "UPDATE intimations" in sql
    assert "WHERE id IN (?, ?)" in sql
    params = mock_con.con.execute.call_args[0][1]
    assert params[-2:] == [1, 2] # The last two are IDs

@pytest.mark.asyncio
async def test_store_batch_empty(analysis_repo, mock_con):
    """Test storing empty batch."""
    await analysis_repo.store_analysis_results_batch([])
    mock_con.insert.assert_not_called()
    mock_con.con.execute.assert_not_called()

@pytest.mark.asyncio
async def test_get_unscored_analyses(analysis_repo, mock_con):
    """Test fetching unscored analyses."""
    # Mock ibis table expression chain
    t_mock = MagicMock()
    mock_con.table.return_value = t_mock

    # Chain: filter -> filter -> limit -> execute -> to_dict
    t_filtered = MagicMock()
    t_mock.filter.return_value = t_filtered
    t_filtered.filter.return_value = t_filtered # Chained filter
    t_limit = MagicMock()
    t_filtered.limit.return_value = t_limit

    mock_df = MagicMock()
    t_limit.execute.return_value = mock_df
    mock_df.to_dict.return_value = [{"id": 1}]

    results = await analysis_repo.get_unscored_analyses(limit=50)

    assert results == [{"id": 1}]
    mock_con.table.assert_called_with("analysis_results")
    t_filtered.limit.assert_called_with(50)

@pytest.mark.asyncio
async def test_get_unscored_analyses_error(analysis_repo, mock_con):
    """Test error handling in get_unscored_analyses."""
    mock_con.table.side_effect = Exception("DB Error")
    results = await analysis_repo.get_unscored_analyses()
    assert results == []

@pytest.mark.asyncio
async def test_mark_analyses_scored(analysis_repo, mock_con):
    """Test marking analyses as scored."""
    ids = [10, 20, 30]
    await analysis_repo.mark_analyses_scored(ids)

    mock_con.con.execute.assert_called_once()
    sql = mock_con.con.execute.call_args[0][0]
    assert "UPDATE analysis_results SET scored = TRUE" in sql
    assert "WHERE id IN (?, ?, ?)" in sql
    params = mock_con.con.execute.call_args[0][1]
    assert params == ids

@pytest.mark.asyncio
async def test_mark_analyses_scored_empty(analysis_repo, mock_con):
    """Test marking empty list."""
    await analysis_repo.mark_analyses_scored([])
    mock_con.con.execute.assert_not_called()
