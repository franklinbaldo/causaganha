import json
import sys
import importlib.util
from unittest.mock import patch, MagicMock

# Hack to import generate-data.py since it has a dash in its name
spec = importlib.util.spec_from_file_location("generate_data", "scripts/dashboard/generate-data.py")
generate_data = importlib.util.module_from_spec(spec)
sys.modules["generate_data"] = generate_data
spec.loader.exec_module(generate_data)


def test_get_incident_status_with_streak():
    mock_response = {
        "workflow_runs": [
            {"conclusion": "failure", "html_url": "url1"},
            {"conclusion": "failure", "html_url": "url2"},
            {"conclusion": "failure", "html_url": "url3"},
            {"conclusion": "success", "html_url": "url4"},
            {"conclusion": "failure", "html_url": "url5"}
        ]
    }

    mock_read = MagicMock()
    mock_read.read.return_value = json.dumps(mock_response).encode('utf-8')

    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value = mock_read

        incident = generate_data.get_incident_status()

        assert incident is not None
        assert incident["streak"] == 3
        assert incident["latest_failing_run_url"] == "url1"
        assert incident["pr_number"] == 436
        assert incident["pr_blocked_by"] == "Kilo Code Review"

def test_get_incident_status_no_streak():
    mock_response = {
        "workflow_runs": [
            {"conclusion": "success", "html_url": "url1"},
            {"conclusion": "failure", "html_url": "url2"}
        ]
    }

    mock_read = MagicMock()
    mock_read.read.return_value = json.dumps(mock_response).encode('utf-8')

    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value = mock_read

        incident = generate_data.get_incident_status()

        assert incident is None

def test_get_incident_status_api_failure():
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_urlopen.side_effect = Exception("API Error")

        incident = generate_data.get_incident_status()

        assert incident is None
