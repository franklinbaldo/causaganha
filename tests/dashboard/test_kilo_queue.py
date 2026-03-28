"""Tests for the Kilo Queue Dashboard generator."""

import json
from datetime import UTC, datetime

import pytest

from scripts.dashboard.generate_kilo_queue import get_kilo_queue


def create_mock_response(data: dict):  # noqa: ANN201
    """Create a mock context manager response object matching urllib.request.urlopen."""

    class MockResponse:
        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):  # noqa: ANN001, ANN204
            pass

        def read(self):  # noqa: ANN202
            return json.dumps(data).encode("utf-8")

    return MockResponse()


@pytest.fixture
def mock_github_api(mocker):  # noqa: ANN001, ANN201
    """Mock the GitHub API responses and current time."""
    # Setup standard mock objects
    mock_urlopen = mocker.patch("urllib.request.urlopen")

    # Mock datetime.now to return a fixed time for age calculations
    mock_datetime = mocker.patch("scripts.dashboard.generate_kilo_queue.datetime")
    fixed_now = datetime(2026, 3, 28, 5, 0, tzinfo=UTC)
    mock_datetime.now.return_value = fixed_now
    mock_datetime.strptime = datetime.strptime
    mock_datetime.UTC = UTC

    return mock_urlopen, fixed_now


def test_kilo_queue_blocked_only_by_kilo(mock_github_api):  # noqa: ANN001, ANN201
    """Verify that PRs blocked only by Kilo are included."""
    mock_urlopen, _ = mock_github_api

    prs = [{"number": 1, "title": "Blocked PR", "head": {"sha": "abc"}, "html_url": "http://pr1"}]
    checks_pr1 = {
        "check_runs": [
            {"name": "lint", "status": "completed", "conclusion": "success", "html_url": ""},
            {"name": "tests", "status": "completed", "conclusion": "success", "html_url": ""},
            {
                "name": "Kilo Code Review",
                "status": "completed",
                "conclusion": "action_required",
                "html_url": "http://kilo1",
                "completed_at": "2026-03-28T04:00:00Z",
                "started_at": "2026-03-28T03:00:00Z",
            },
        ]
    }

    mock_urlopen.side_effect = [create_mock_response(prs), create_mock_response(checks_pr1)]
    result = get_kilo_queue()

    assert result["metrics"]["total"] == 1  # noqa: S101
    assert len(result["prs"]) == 1  # noqa: S101
    pr = result["prs"][0]
    assert pr["number"] == 1  # noqa: S101
    assert pr["title"] == "Blocked PR"  # noqa: S101
    assert pr["kilo_url"] == "http://kilo1"  # noqa: S101
    assert pr["age_mins"] == 60  # noqa: S101, PLR2004
    assert pr["bucket"] == "warning"  # noqa: S101


def test_kilo_queue_other_checks_failed(mock_github_api):  # noqa: ANN001, ANN201
    """Verify that PRs with other failed checks are excluded."""
    mock_urlopen, _ = mock_github_api

    prs = [{"number": 2, "title": "Failed PR", "head": {"sha": "def"}, "html_url": "http://pr2"}]
    checks_pr2 = {
        "check_runs": [
            {"name": "lint", "status": "completed", "conclusion": "failure", "html_url": ""},
            {
                "name": "Kilo Code Review",
                "status": "completed",
                "conclusion": "action_required",
                "html_url": "http://kilo2",
                "completed_at": "2026-03-28T04:00:00Z",
            },
        ]
    }

    mock_urlopen.side_effect = [create_mock_response(prs), create_mock_response(checks_pr2)]
    result = get_kilo_queue()

    assert result["metrics"]["total"] == 0  # noqa: S101
    assert len(result["prs"]) == 0  # noqa: S101


def test_kilo_queue_kilo_passed(mock_github_api):  # noqa: ANN001, ANN201
    """Verify that PRs where Kilo passes are excluded."""
    mock_urlopen, _ = mock_github_api

    prs = [{"number": 3, "title": "Green PR", "head": {"sha": "ghi"}, "html_url": "http://pr3"}]
    checks = {
        "check_runs": [
            {
                "name": "Kilo Code Review",
                "status": "completed",
                "conclusion": "success",
                "html_url": "",
            }
        ]
    }

    mock_urlopen.side_effect = [create_mock_response(prs), create_mock_response(checks)]
    result = get_kilo_queue()
    assert result["metrics"]["total"] == 0  # noqa: S101


def test_kilo_queue_age_buckets(mock_github_api):  # noqa: ANN001, ANN201
    """Verify that age calculations correctly bucket PRs into fresh, warning, and stale."""
    mock_urlopen, _ = mock_github_api

    prs = [
        {"number": 1, "title": "Fresh PR", "head": {"sha": "1"}, "html_url": "http://1"},
        {"number": 2, "title": "Warning PR", "head": {"sha": "2"}, "html_url": "http://2"},
        {"number": 3, "title": "Stale PR", "head": {"sha": "3"}, "html_url": "http://3"},
    ]

    checks_1 = {
        "check_runs": [
            {
                "name": "Kilo Code Review",
                "status": "completed",
                "conclusion": "action_required",
                "html_url": "",
                "completed_at": "2026-03-28T04:30:00Z",
            }
        ]
    }
    checks_2 = {
        "check_runs": [
            {
                "name": "Kilo Code Review",
                "status": "completed",
                "conclusion": "action_required",
                "html_url": "",
                "completed_at": "2026-03-28T03:30:00Z",
            }
        ]
    }
    checks_3 = {
        "check_runs": [
            {
                "name": "Kilo Code Review",
                "status": "completed",
                "conclusion": "action_required",
                "html_url": "",
                "completed_at": "2026-03-28T02:30:00Z",
            }
        ]
    }

    mock_urlopen.side_effect = [
        create_mock_response(prs),
        create_mock_response(checks_1),
        create_mock_response(checks_2),
        create_mock_response(checks_3),
    ]

    result = get_kilo_queue()

    assert result["metrics"]["total"] == 3  # noqa: S101, PLR2004
    assert result["metrics"]["max_age_mins"] == 150  # noqa: S101, PLR2004
    assert result["metrics"]["avg_age_mins"] == 90.0  # noqa: S101, PLR2004

    assert result["prs"][0]["number"] == 3  # noqa: S101, PLR2004
    assert result["prs"][0]["bucket"] == "stale"  # noqa: S101
    assert result["prs"][0]["age_mins"] == 150  # noqa: S101, PLR2004

    assert result["prs"][1]["number"] == 2  # noqa: S101, PLR2004
    assert result["prs"][1]["bucket"] == "warning"  # noqa: S101
    assert result["prs"][1]["age_mins"] == 90  # noqa: S101, PLR2004

    assert result["prs"][2]["number"] == 1  # noqa: S101
    assert result["prs"][2]["bucket"] == "fresh"  # noqa: S101
    assert result["prs"][2]["age_mins"] == 30  # noqa: S101, PLR2004
