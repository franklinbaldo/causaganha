import importlib.util
import json
import sys
from unittest.mock import MagicMock, patch

import pytest


# Load generate-data.py dynamically
spec = importlib.util.spec_from_file_location("generate_data", "scripts/dashboard/generate-data.py")
module = importlib.util.module_from_spec(spec)
sys.modules["generate_data"] = module
spec.loader.exec_module(module)

@pytest.fixture(autouse=True)
def reload_module() -> None:
    spec.loader.exec_module(module)


@patch("urllib.request.urlopen")
def test_fetch_kilo_ready_count_all_success(mock_urlopen) -> None:
    """Test when PR has successful checks except Kilo."""
    # Mock PR list response
    mock_prs_response = MagicMock()
    mock_prs_response.read.return_value = json.dumps([
        {"number": 1, "head": {"sha": "sha1"}}
    ]).encode("utf-8")

    # Mock Checks response
    mock_checks_response = MagicMock()
    mock_checks_response.read.return_value = json.dumps({
        "check_runs": [
            {"name": "lint", "status": "completed", "conclusion": "success"},
            {"name": "Kilo Code Review", "status": "completed", "conclusion": "action_required"}
        ]
    }).encode("utf-8")

    # Configure the mock to return PRs first, then checks
    mock_urlopen.side_effect = [
        MagicMock(__enter__=lambda _: mock_prs_response, __exit__=lambda *args: None),
        MagicMock(__enter__=lambda _: mock_checks_response, __exit__=lambda *args: None)
    ]

    count = module.fetch_kilo_ready_count()
    assert count == 1


@patch("urllib.request.urlopen")
def test_fetch_kilo_ready_count_with_failures(mock_urlopen) -> None:
    """Test when PR has other failures besides Kilo."""
    # Mock PR list response
    mock_prs_response = MagicMock()
    mock_prs_response.read.return_value = json.dumps([
        {"number": 1, "head": {"sha": "sha1"}}
    ]).encode("utf-8")

    # Mock Checks response with a failure
    mock_checks_response = MagicMock()
    mock_checks_response.read.return_value = json.dumps({
        "check_runs": [
            {"name": "lint", "status": "completed", "conclusion": "failure"},
            {"name": "Kilo Code Review", "status": "completed", "conclusion": "action_required"}
        ]
    }).encode("utf-8")

    # Configure the mock
    mock_urlopen.side_effect = [
        MagicMock(__enter__=lambda _: mock_prs_response, __exit__=lambda *args: None),
        MagicMock(__enter__=lambda _: mock_checks_response, __exit__=lambda *args: None)
    ]

    count = module.fetch_kilo_ready_count()
    assert count == 0


@patch("urllib.request.urlopen")
def test_fetch_kilo_ready_count_pending_checks(mock_urlopen) -> None:
    """Test when PR has pending checks."""
    mock_prs_response = MagicMock()
    mock_prs_response.read.return_value = json.dumps([
        {"number": 1, "head": {"sha": "sha1"}}
    ]).encode("utf-8")

    mock_checks_response = MagicMock()
    mock_checks_response.read.return_value = json.dumps({
        "check_runs": [
            {"name": "lint", "status": "in_progress", "conclusion": None},
            {"name": "Kilo Code Review", "status": "completed", "conclusion": "action_required"}
        ]
    }).encode("utf-8")

    mock_urlopen.side_effect = [
        MagicMock(__enter__=lambda _: mock_prs_response, __exit__=lambda *args: None),
        MagicMock(__enter__=lambda _: mock_checks_response, __exit__=lambda *args: None)
    ]

    count = module.fetch_kilo_ready_count()
    assert count == 0


@patch("urllib.request.urlopen")
def test_fetch_kilo_ready_count_empty_checks(mock_urlopen) -> None:
    """Test when PR has no checks yet."""
    mock_prs_response = MagicMock()
    mock_prs_response.read.return_value = json.dumps([
        {"number": 1, "head": {"sha": "sha1"}}
    ]).encode("utf-8")

    mock_checks_response = MagicMock()
    mock_checks_response.read.return_value = json.dumps({
        "check_runs": []
    }).encode("utf-8")

    mock_urlopen.side_effect = [
        MagicMock(__enter__=lambda _: mock_prs_response, __exit__=lambda *args: None),
        MagicMock(__enter__=lambda _: mock_checks_response, __exit__=lambda *args: None)
    ]

    count = module.fetch_kilo_ready_count()
    assert count == 0


@patch("urllib.request.urlopen")
def test_fetch_kilo_ready_count_kilo_success(mock_urlopen) -> None:
    """Test when Kilo check is successful."""
    mock_prs_response = MagicMock()
    mock_prs_response.read.return_value = json.dumps([
        {"number": 1, "head": {"sha": "sha1"}}
    ]).encode("utf-8")

    mock_checks_response = MagicMock()
    mock_checks_response.read.return_value = json.dumps({
        "check_runs": [
            {"name": "lint", "status": "completed", "conclusion": "success"},
            {"name": "Kilo Code Review", "status": "completed", "conclusion": "success"}
        ]
    }).encode("utf-8")

    mock_urlopen.side_effect = [
        MagicMock(__enter__=lambda _: mock_prs_response, __exit__=lambda *args: None),
        MagicMock(__enter__=lambda _: mock_checks_response, __exit__=lambda *args: None)
    ]

    count = module.fetch_kilo_ready_count()
    assert count == 0
