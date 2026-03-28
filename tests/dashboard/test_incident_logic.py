"""Tests for the dashboard incident logic."""
import importlib.util
import json
import sys
from unittest.mock import MagicMock, patch


# Note: We import generate-data.py using spec_from_file_location since it has a dash in its name
spec = importlib.util.spec_from_file_location("generate_data", "scripts/dashboard/generate-data.py")
if spec is None or spec.loader is None:
    msg = "Could not find scripts/dashboard/generate-data.py"
    raise ImportError(msg)
generate_data = importlib.util.module_from_spec(spec)
sys.modules["generate_data"] = generate_data
spec.loader.exec_module(generate_data)


def test_get_incident_status_with_streak() -> None:
    """Test incident status correctly parses a failure streak."""
    mock_response = {
        "workflow_runs": [
            {"conclusion": "failure", "html_url": "url1"},
            {"conclusion": "failure", "html_url": "url2"},
            {"conclusion": "failure", "html_url": "url3"},
            {"conclusion": "success", "html_url": "url4"},
            {"conclusion": "failure", "html_url": "url5"},
        ]
    }

    mock_read = MagicMock()
    mock_read.read.return_value = json.dumps(mock_response).encode("utf-8")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value = mock_read

        incident = generate_data.get_incident_status()

        assert incident is not None  # noqa: S101
        assert incident["streak"] == 3  # noqa: S101, PLR2004
        assert incident["latest_failing_run_url"] == "url1"  # noqa: S101
        assert incident["pr_number"] == 436  # noqa: S101, PLR2004
        assert incident["pr_blocked_by"] == "Kilo Code Review"  # noqa: S101


def test_get_incident_status_no_streak() -> None:
    """Test incident status returns None when there is no failure streak."""
    mock_response = {
        "workflow_runs": [
            {"conclusion": "success", "html_url": "url1"},
            {"conclusion": "failure", "html_url": "url2"},
        ]
    }

    mock_read = MagicMock()
    mock_read.read.return_value = json.dumps(mock_response).encode("utf-8")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value = mock_read

        incident = generate_data.get_incident_status()

        assert incident is None  # noqa: S101


def test_get_incident_status_api_failure() -> None:
    """Test incident status handles API failures gracefully."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = Exception("API Error")

        incident = generate_data.get_incident_status()

        assert incident is None  # noqa: S101
