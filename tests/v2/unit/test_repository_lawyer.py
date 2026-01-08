"""Unit tests for LawyerRatingRepository."""

import asyncio
from unittest.mock import MagicMock, call

import pytest
from ibis import BaseBackend

from causaganha.storage.repositories.lawyer import LawyerRatingRepository


@pytest.fixture
def mock_con():
    """Mock Ibis connection."""
    con = MagicMock(spec=BaseBackend)
    con.con = MagicMock()
    return con

@pytest.fixture
def lawyer_repo(mock_con):
    """LawyerRatingRepository instance."""
    return LawyerRatingRepository(mock_con)

@pytest.mark.asyncio
async def test_get_lawyer_ratings_empty(lawyer_repo, mock_con):
    """Test getting ratings with empty list."""
    results = await lawyer_repo.get_lawyer_ratings([])
    assert results == []
    mock_con.table.assert_not_called()

@pytest.mark.asyncio
async def test_get_lawyer_ratings(lawyer_repo, mock_con):
    """Test getting lawyer ratings."""
    t_mock = MagicMock()
    mock_con.table.return_value = t_mock

    # Mock chain
    t_filtered = MagicMock()
    t_mock.filter.return_value = t_filtered

    mock_df = MagicMock()
    t_filtered.execute.return_value = mock_df

    # Mock data return
    db_records = [
        {"oab_number": "123", "oab_state": "SP", "mu": 25.0},
        {"oab_number": "456", "oab_state": "RJ", "mu": 30.0},
        {"oab_number": "789", "oab_state": "MG", "mu": 20.0}, # Extra one
    ]
    mock_df.to_dict.return_value = db_records

    # Request
    request_oabs = [("123", "SP"), ("456", "RJ")]
    results = await lawyer_repo.get_lawyer_ratings(request_oabs)

    assert len(results) == 2
    assert {"oab_number": "123", "oab_state": "SP", "mu": 25.0} in results
    assert {"oab_number": "456", "oab_state": "RJ", "mu": 30.0} in results

    mock_con.table.assert_called_with("lawyer_ratings")

@pytest.mark.asyncio
async def test_get_lawyer_ratings_error(lawyer_repo, mock_con):
    """Test error handling in get_lawyer_ratings."""
    mock_con.table.side_effect = Exception("DB Error")
    results = await lawyer_repo.get_lawyer_ratings([("123", "SP")])
    assert results == []

@pytest.mark.asyncio
async def test_save_lawyer_ratings_empty(lawyer_repo, mock_con):
    """Test saving empty ratings."""
    await lawyer_repo.save_lawyer_ratings([])
    mock_con.con.execute.assert_not_called()

@pytest.mark.asyncio
async def test_save_lawyer_ratings(lawyer_repo, mock_con):
    """Test saving lawyer ratings."""
    ratings = [
        {
            "oab_number": "123", "oab_state": "SP", "lawyer_name": "Test",
            "mu": 25.0, "sigma": 8.33,
            "total_cases": 1, "wins": 1, "losses": 0
        },
        {
            "oab_number": "456", "oab_state": "RJ", "lawyer_name": "Test 2",
            "mu": 22.0, "sigma": 8.0,
            "total_cases": 2, "wins": 0, "losses": 2
        }
    ]

    await lawyer_repo.save_lawyer_ratings(ratings)

    assert mock_con.con.execute.call_count == 2

    # Verify SQL structure (checking first call)
    sql = mock_con.con.execute.call_args_list[0][0][0]
    assert "INSERT INTO lawyer_ratings" in sql
    assert "ON CONFLICT (oab_number, oab_state) DO UPDATE" in sql

    params = mock_con.con.execute.call_args_list[0][0][1]
    assert params[0] == "123"
    assert params[1] == "SP"
