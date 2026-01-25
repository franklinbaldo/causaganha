"""Tests for CLI commands."""

from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from causaganha.cli import app


runner = CliRunner()


@pytest.fixture
def mock_db_connection() -> Generator[MagicMock, None, None]:
    """Mock DB connection fixture."""
    with patch("causaganha.cli.get_connection") as mock_get:
        mock_con = MagicMock()
        mock_get.return_value = mock_con
        yield mock_con


def test_db_status(mock_db_connection: MagicMock) -> None:
    """Test db status command."""
    mock_db_connection.list_tables.return_value = ["table1", "table2"]
    result = runner.invoke(app, ["db", "status"])
    assert result.exit_code == 0
    assert "Found tables: ['table1', 'table2']" in result.stdout


def test_db_unknown_action(mock_db_connection: MagicMock) -> None:
    """Test db command with unknown action."""
    result = runner.invoke(app, ["db", "unknown"])
    assert result.exit_code == 0
    assert "Unknown action: unknown" in result.stdout


def test_score_command() -> None:
    """Test score command."""
    with patch("causaganha.cli.calculate_ratings", new_callable=AsyncMock) as mock_calc:
        result = runner.invoke(app, ["score", "--limit", "10"])
        assert result.exit_code == 0
        mock_calc.assert_called_once_with(batch_size=10)


def test_analyze_command() -> None:
    """Test analyze command."""
    with patch("causaganha.cli.analyze_pending_decisions", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = {
            "strategy": "hybrid",
            "analyzed": 1,
            "failed": 0,
            "rag_used": 1,
            "llm_used": 0,
            "total_cost": 0.01,
            "cost_per_decision": 0.01,
            "savings_vs_llm_pct": 50.0,
        }
        result = runner.invoke(app, ["analyze", "--limit", "5", "--strategy", "hybrid"])
        assert result.exit_code == 0
        assert "Analysis complete!" in result.stdout
        mock_analyze.assert_called_once()


def test_collect_command_disabled() -> None:
    """Test collect command prints disabled message."""
    result = runner.invoke(app, ["collect"])
    assert result.exit_code == 0
    assert "Collection currently disabled" in result.stdout


def test_groundtruth_init() -> None:
    """Test groundtruth init command."""
    with patch("causaganha.analysis.ground_truth.GroundTruthManager") as mock_manager_cls:
        mock_manager = mock_manager_cls.return_value
        result = runner.invoke(app, ["groundtruth", "init", "--overwrite"])
        assert result.exit_code == 0
        assert "Ground truth vector store initialized" in result.stdout
        mock_manager.init_store.assert_called_once_with(overwrite=True)


def test_groundtruth_sync() -> None:
    """Test groundtruth sync command."""
    with patch("causaganha.analysis.ground_truth.GroundTruthManager") as mock_manager_cls:
        mock_manager = mock_manager_cls.return_value
        mock_manager.sync_from_db = AsyncMock(return_value={"synced": 5, "status": "success"})

        result = runner.invoke(app, ["groundtruth", "sync", "--limit", "10"])

        assert result.exit_code == 0
        assert "Sync complete! Added 5 new examples" in result.stdout
        mock_manager.sync_from_db.assert_called_once()


def test_groundtruth_search() -> None:
    """Test groundtruth search command."""
    with patch("causaganha.analysis.ground_truth.GroundTruthManager") as mock_manager_cls:
        mock_manager = mock_manager_cls.return_value
        mock_manager.search = AsyncMock(
            return_value=[
                {"text": "Sample text", "outcome": "WIN", "score": 0.9},
            ],
        )

        result = runner.invoke(app, ["groundtruth", "search", "test query"])

        assert result.exit_code == 0
        assert "Sample text" in result.stdout
        assert "WIN" in result.stdout
        mock_manager.search.assert_called_once_with("test query", k=5)
