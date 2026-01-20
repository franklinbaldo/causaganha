"""End-to-end tests for the CLI."""

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from causaganha.cli import app

runner = CliRunner()


def test_collect_command() -> None:
    """Test collect command."""
    with patch("causaganha.cli.collect_metadata_for_all_courts") as mock_collect:
        mock_collect.return_value = []
        result = runner.invoke(app, ["collect", "--days-back", "5", "--courts", "TJRO,TJMT"])

        assert result.exit_code == 0
        mock_collect.assert_called_once()
        args, _ = mock_collect.call_args
        assert set(args[0]) == {"TJRO", "TJMT"}
        assert args[1] == 5


def test_archive_command() -> None:
    """Test archive command."""
    with patch("causaganha.cli.archive_documents") as mock_archive:
        # It needs to return a dict as per type hint, but CLI doesn't use return value much
        mock_archive.return_value = {"status": "success"}

        # We also need to patch create_archive_service and DocumentService inside CLI or just let them run?
        # CLI instantiates them.
        #     doc_service = DocumentService()
        #     archive_service = create_archive_service()
        # If we let them run, they might try to connect to real services.
        # But archive_documents is mocked, so it won't use them.
        # However, instantiation might fail if configs are missing.
        # Let's mock the services to be safe.

        with patch("causaganha.cli.DocumentService"), \
             patch("causaganha.cli.create_archive_service"):

            result = runner.invoke(app, ["archive", "--limit", "20", "--dry-run"])

            assert result.exit_code == 0
            mock_archive.assert_called_once()
            _, kwargs = mock_archive.call_args
            assert kwargs["limit"] == 20
            assert kwargs["dry_run"] is True


def test_analyze_command() -> None:
    """Test analyze command."""
    with patch("causaganha.cli.analyze_pending_decisions") as mock_analyze:
        mock_analyze.return_value = {
            "strategy": "hybrid",
            "analyzed": 10,
            "failed": 0,
            "rag_used": 5,
            "llm_used": 5,
            "total_cost": 0.1,
            "cost_per_decision": 0.01,
            "savings_vs_llm_pct": 50.0,
        }

        result = runner.invoke(app, ["analyze", "--limit", "50", "--strategy", "hybrid"])

        if result.exit_code != 0:
            print(result.stdout)
            print(result.exception)

        assert result.exit_code == 0
        assert "Analysis complete" in result.stdout
        mock_analyze.assert_called_once()
        _, kwargs = mock_analyze.call_args
        assert kwargs["batch_size"] == 50
        assert kwargs["strategy"] == "hybrid"


def test_score_command() -> None:
    """Test score command."""
    with patch("causaganha.cli.calculate_ratings") as mock_score:
        result = runner.invoke(app, ["score", "--limit", "200"])

        assert result.exit_code == 0
        mock_score.assert_called_once()
        _, kwargs = mock_score.call_args
        assert kwargs["batch_size"] == 200


def test_pipeline_command() -> None:
    """Test full pipeline command."""
    with patch("causaganha.cli.collect_metadata_for_all_courts") as mock_collect, \
         patch("causaganha.cli.archive_documents") as mock_archive, \
         patch("causaganha.cli.analyze_pending_decisions") as mock_analyze, \
         patch("causaganha.cli.calculate_ratings") as mock_score, \
         patch("causaganha.cli.DocumentService"), \
         patch("causaganha.cli.create_archive_service"):

        mock_collect.return_value = []
        mock_archive.return_value = {"status": "success"}
        mock_analyze.return_value = {
            "strategy": "hybrid", "analyzed": 0, "failed": 0,
            "rag_used": 0, "llm_used": 0, "total_cost": 0,
            "cost_per_decision": 0, "savings_vs_llm_pct": 0
        }

        result = runner.invoke(app, ["pipeline", "--days-back", "3", "--analyze-limit", "15"])

        assert result.exit_code == 0
        assert "Pipeline complete" in result.stdout

        mock_collect.assert_called_once()
        mock_archive.assert_called_once()
        mock_analyze.assert_called_once()
        mock_score.assert_called_once()

        # Verify arguments propagation
        assert mock_collect.call_args[0][1] == 3  # days_back
        assert mock_analyze.call_args[1]["batch_size"] == 15
