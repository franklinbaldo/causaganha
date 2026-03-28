import json
import os
import sys
from unittest.mock import MagicMock, patch


# Make scripts discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import importlib.util


spec = importlib.util.spec_from_file_location("generate_data", "scripts/dashboard/generate-data.py")
generate_data = importlib.util.module_from_spec(spec)
sys.modules["generate_data"] = generate_data
spec.loader.exec_module(generate_data)


@patch("generate_data.get_connection")
@patch("urllib.request.urlopen")
def test_generate_data_incident_metrics(mock_urlopen, mock_get_connection, tmp_path):
    # Just raise an error when trying to connect to mock so it goes to "if con" block as false
    mock_get_connection.side_effect = Exception("No DB in test")

    mock_runs_response = MagicMock()
    mock_runs_response.read.return_value = json.dumps(
        {
            "workflow_runs": [
                {"conclusion": "failure", "html_url": "http://run/2"},
                {"conclusion": "failure", "html_url": "http://run/1"},
                {"conclusion": "success"},
            ]
        }
    ).encode()

    mock_prs_response = MagicMock()
    mock_prs_response.read.return_value = json.dumps([{"head": {"sha": "abc1234"}}]).encode()

    mock_checks_response = MagicMock()
    mock_checks_response.read.return_value = json.dumps(
        {
            "check_runs": [
                {"name": "Kilo Code Review", "conclusion": "failure"},
                {"name": "Other Test", "status": "completed", "conclusion": "success"},
            ]
        }
    ).encode()

    def side_effect(req, timeout=None):
        url = req.full_url
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp

        if "workflows/collect-zips.yml/runs" in url:
            mock_resp.read = mock_runs_response.read
        elif "/pulls?state=open" in url:
            mock_resp.read = mock_prs_response.read
        elif "check-runs" in url:
            mock_resp.read = mock_checks_response.read
        else:
            mock_resp.read.return_value = b"{}"

        return mock_resp

    mock_urlopen.side_effect = side_effect

    db_path = tmp_path / "test.db"
    out_path = tmp_path / "dashboard-data.json"

    generate_data.generate_dashboard_data(db_path, out_path)

    perf_path = tmp_path / "perf-metrics.json"
    assert perf_path.exists()

    metrics = json.loads(perf_path.read_text())
    assert "incident" in metrics
    incident = metrics["incident"]

    assert incident["active"] is True
    assert incident["collect_failure_streak"] == 2
    assert incident["severity"] == "warning"
    assert incident["latest_failure_url"] == "http://run/2"

    assert incident["causaganha_kilo_ready_count"] == 1
    assert incident["remaining_blocker"] == "Kilo Code Review"
