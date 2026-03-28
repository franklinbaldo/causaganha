import importlib.util
import json
import os

# Adjust the import to access generate_dashboard_data or extract its logic
# We can mock get_connection and write tests by overriding output paths
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Load module dynamically because of dash in filename
spec = importlib.util.spec_from_file_location("generate_data", "scripts/dashboard/generate-data.py")
generate_data = importlib.util.module_from_spec(spec)
sys.modules["generate_data"] = generate_data
spec.loader.exec_module(generate_data)
generate_dashboard_data = generate_data.generate_dashboard_data


@patch("generate_data.get_connection")
def test_calculate_streak_and_last_success(mock_get_connection, tmp_path):
    # Mocking database connection to avoid DB errors
    mock_con = MagicMock()
    # Mock db fetchone response to prevent MagicMock comparison issues
    mock_con.execute.return_value.fetchone.return_value = ["2024-01-01", "2024-01-02", 2, 100]
    mock_con.execute.return_value.fetchall.return_value = []
    mock_get_connection.return_value.con = mock_con

    # Prepare dummy run_stats.json content
    run_stats = [
        {"conclusion": "failure", "createdAt": "2026-03-25T12:00:00Z"},
        {"conclusion": "failure", "createdAt": "2026-03-26T12:00:00Z"},
        {"conclusion": "success", "createdAt": "2026-03-24T12:00:00Z"},
        {"conclusion": "success", "createdAt": "2026-03-23T12:00:00Z"},
    ]

    # Change CWD or mock the Path("run_stats.json")
    with patch("generate_data.Path") as MockPath:
        # Mock paths used in the script
        db_path = tmp_path / "causaganha.duckdb"
        output_path = tmp_path / "dashboard" / "public" / "dashboard-data.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # We need to correctly mock run_stats_path.exists() and read_text()
        def mock_path_side_effect(arg):
            if str(arg) == "run_stats.json":
                mock_run_stats = MagicMock()
                mock_run_stats.exists.return_value = True
                mock_run_stats.read_text.return_value = json.dumps(run_stats)
                return mock_run_stats
            # Return real Path object for other paths
            return Path(arg)

        MockPath.side_effect = mock_path_side_effect

        # Mock fetch_progress_json since we don't want to make real network requests
        with patch("generate_data.fetch_progress_json", return_value={}):
            generate_dashboard_data(db_path, output_path)

        # Check perf-metrics.json
        perf_metrics_path = output_path.parent / "perf-metrics.json"
        assert perf_metrics_path.exists()

        metrics = json.loads(perf_metrics_path.read_text())
        assert metrics["causaganha_current_failure_streak"] == 2
        assert metrics["causaganha_last_successful_run_iso"] == "2026-03-24T12:00:00Z"
        assert metrics["causaganha_last_successful_run_label"] == "24/03/2026 12:00 UTC"
        assert metrics["causaganha_was_restored"] is False


@patch("generate_data.get_connection")
def test_calculate_streak_zero_on_success(mock_get_connection, tmp_path):
    mock_con = MagicMock()
    mock_con.execute.return_value.fetchone.return_value = ["2024-01-01", "2024-01-02", 2, 100]
    mock_con.execute.return_value.fetchall.return_value = []
    mock_get_connection.return_value.con = mock_con

    # Run stats with a success at the top
    run_stats = [
        {"conclusion": "success", "createdAt": "2026-03-26T12:00:00Z"},
        {"conclusion": "failure", "createdAt": "2026-03-25T12:00:00Z"},
    ]

    with patch("generate_data.Path") as MockPath:
        db_path = tmp_path / "causaganha.duckdb"
        output_path = tmp_path / "dashboard" / "public" / "dashboard-data.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        def mock_path_side_effect(arg):
            if str(arg) == "run_stats.json":
                mock_run_stats = MagicMock()
                mock_run_stats.exists.return_value = True
                mock_run_stats.read_text.return_value = json.dumps(run_stats)
                return mock_run_stats
            return Path(arg)

        MockPath.side_effect = mock_path_side_effect

        with patch("generate_data.fetch_progress_json", return_value={}):
            generate_dashboard_data(db_path, output_path)

        perf_metrics_path = output_path.parent / "perf-metrics.json"
        metrics = json.loads(perf_metrics_path.read_text())

        assert metrics["causaganha_current_failure_streak"] == 0
        assert metrics["causaganha_last_successful_run_iso"] == "2026-03-26T12:00:00Z"
        assert metrics["causaganha_last_successful_run_label"] == "26/03/2026 12:00 UTC"
        assert metrics["causaganha_was_restored"] is False


@patch("generate_data.get_connection")
def test_calculate_was_restored(mock_get_connection, tmp_path):
    mock_con = MagicMock()
    mock_con.execute.return_value.fetchone.return_value = ["2024-01-01", "2024-01-02", 2, 100]
    mock_con.execute.return_value.fetchall.return_value = []
    mock_get_connection.return_value.con = mock_con

    from datetime import UTC, datetime, timedelta

    # Create a success very recently, preceded by a failure
    recent_dt = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2)
    recent_iso = recent_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    run_stats = [
        {"conclusion": "success", "createdAt": recent_iso},
        {"conclusion": "failure", "createdAt": "2026-03-25T12:00:00Z"},
    ]

    with patch("generate_data.Path") as MockPath:
        db_path = tmp_path / "causaganha.duckdb"
        output_path = tmp_path / "dashboard" / "public" / "dashboard-data.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        def mock_path_side_effect(arg):
            if str(arg) == "run_stats.json":
                mock_run_stats = MagicMock()
                mock_run_stats.exists.return_value = True
                mock_run_stats.read_text.return_value = json.dumps(run_stats)
                return mock_run_stats
            return Path(arg)

        MockPath.side_effect = mock_path_side_effect

        with patch("generate_data.fetch_progress_json", return_value={}):
            generate_dashboard_data(db_path, output_path)

        perf_metrics_path = output_path.parent / "perf-metrics.json"
        metrics = json.loads(perf_metrics_path.read_text())

        assert metrics["causaganha_current_failure_streak"] == 0
        assert metrics["causaganha_last_successful_run_iso"] == recent_iso
        assert metrics["causaganha_was_restored"] is True
