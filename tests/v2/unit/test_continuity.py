"""Unit tests for ContinuityManager."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from ibis import BaseBackend

from causaganha.pipeline.continuity import ContinuityManager


@pytest.fixture
def mock_con():
    """Mock Ibis connection."""
    con = MagicMock(spec=BaseBackend)
    con.con = MagicMock()
    return con

@pytest.fixture
def continuity_manager(mock_con):
    """ContinuityManager instance."""
    return ContinuityManager(con=mock_con)

def test_initialization_default():
    """Test initialization without connection creates one."""
    with patch("causaganha.pipeline.continuity.get_connection") as mock_get_con, \
         patch("causaganha.pipeline.continuity.create_schema") as mock_create_schema:

        mock_con_instance = MagicMock()
        mock_get_con.return_value = mock_con_instance

        cm = ContinuityManager()

        assert cm.con == mock_con_instance
        mock_create_schema.assert_called_once_with(mock_con_instance)

def test_is_done_true(continuity_manager, mock_con):
    """Test is_done returns True when record exists."""
    t_mock = MagicMock()
    mock_con.table.return_value = t_mock

    # Chain: filter -> count -> execute
    t_filtered = MagicMock()
    t_mock.filter.return_value = t_filtered
    t_count = MagicMock()
    t_filtered.count.return_value = t_count
    t_count.execute.return_value = 1

    result = continuity_manager.is_done("task1", "step1")

    assert result is True
    mock_con.table.assert_called_with("pipeline_state")
    # Verify filter args could be complex expressions, just check call happened
    t_mock.filter.assert_called()

def test_is_done_false(continuity_manager, mock_con):
    """Test is_done returns False when no record."""
    t_mock = MagicMock()
    mock_con.table.return_value = t_mock

    t_filtered = MagicMock()
    t_mock.filter.return_value = t_filtered
    t_count = MagicMock()
    t_filtered.count.return_value = t_count
    t_count.execute.return_value = 0

    result = continuity_manager.is_done("task1", "step1")

    assert result is False

def test_mark_done_new(continuity_manager, mock_con):
    """Test marking a new task as done."""
    # Mock is_done to return False first
    with patch.object(continuity_manager, "is_done", return_value=False) as mock_is_done:
        continuity_manager.mark_done("task1", "step1")

        mock_is_done.assert_called_with("task1", "step1")
        mock_con.con.execute.assert_called_once()

        sql = mock_con.con.execute.call_args[0][0]
        params = mock_con.con.execute.call_args[0][1]

        assert "INSERT INTO pipeline_state" in sql
        assert params[0] == "task1"
        assert params[1] == "step1"
        assert isinstance(params[2], datetime)

def test_mark_done_existing(continuity_manager, mock_con):
    """Test marking an existing task as done (idempotency)."""
    with patch.object(continuity_manager, "is_done", return_value=True):
        continuity_manager.mark_done("task1", "step1")

        mock_con.con.execute.assert_not_called()
