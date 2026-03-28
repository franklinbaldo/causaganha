"""Tests for the check_pr_lint_status script."""

# ruff: noqa: S101

from __future__ import annotations

import sys

# Add scripts directory to path to import check_pr_lint_status
from pathlib import Path
from unittest.mock import MagicMock, patch


scripts_dir = str(Path(__file__).parent.parent.parent / "scripts" / "dev")
sys.path.insert(0, scripts_dir)

from check_pr_lint_status import analyze_checks, classify_pr_checks  # noqa: E402


def test_analyze_checks_all_pass() -> None:
    """Test when all checks pass."""
    checks = [
        {"name": "lint", "conclusion": "success"},
        {"name": "docs", "conclusion": "success"},
        {"name": "tests (tjro)", "conclusion": "success"},
    ]
    result = analyze_checks(123, checks)
    assert result == "PR #123: all checks passed."


def test_analyze_checks_only_lint_fails() -> None:
    """Test when only lint fails and other standard checks pass."""
    checks = [
        {"name": "lint", "conclusion": "failure"},
        {"name": "docs", "conclusion": "success"},
        {"name": "tests (tjro)", "conclusion": "success"},
    ]
    result = analyze_checks(123, checks)
    assert "PR #123: mechanical lint failure" in result
    assert "docs/tests green" in result
    assert "safe follow-up patch recommended" in result


def test_analyze_checks_lint_and_kilo_fail() -> None:
    """Test when lint and Kilo Code Review fail (like PR 437)."""
    checks = [
        {"name": "lint", "conclusion": "failure"},
        {"name": "docs", "conclusion": "success"},
        {"name": "tests (tjro)", "conclusion": "success"},
        {"name": "Kilo Code Review", "conclusion": "action_required"},
        {"name": "CodeQL", "conclusion": "success"},
    ]
    result = analyze_checks(437, checks)
    assert "PR #437: mechanical lint failure" in result
    assert "codeql/docs/tests green" in result
    assert "safe follow-up patch recommended" in result


def test_analyze_checks_logical_failure() -> None:
    """Test when a non-lint check fails."""
    checks = [
        {"name": "lint", "conclusion": "success"},
        {"name": "docs", "conclusion": "success"},
        {"name": "tests (tjro)", "conclusion": "failure"},
    ]
    result = analyze_checks(123, checks)
    assert "PR #123: logical or non-lint failures present" in result
    assert "['tests (tjro)']" in result


def test_analyze_checks_multiple_failures() -> None:
    """Test when lint and a logical check fail."""
    checks = [
        {"name": "lint", "conclusion": "failure"},
        {"name": "docs", "conclusion": "success"},
        {"name": "tests (tjro)", "conclusion": "failure"},
    ]
    result = analyze_checks(123, checks)
    assert "PR #123: logical or non-lint failures present" in result
    assert "'lint'" in result
    assert "'tests (tjro)'" in result


def test_analyze_checks_kilo_fails_only() -> None:
    """Test when only Kilo Code Review fails."""
    checks = [
        {"name": "lint", "conclusion": "success"},
        {"name": "docs", "conclusion": "success"},
        {"name": "tests (tjro)", "conclusion": "success"},
        {"name": "Kilo Code Review", "conclusion": "action_required"},
    ]
    result = analyze_checks(123, checks)
    assert "PR #123: no lint failure. Other blocked checks: ['Kilo Code Review']" in result


@patch("check_pr_lint_status.fetch_json")
def test_classify_pr_checks(mock_fetch_json: MagicMock) -> None:
    """Test classify_pr_checks fetches correct data and analyzes it."""
    # Setup mock returns
    mock_fetch_json.side_effect = [
        # First call: PR data
        {"head": {"sha": "mocksha123"}},
        # Second call: Checks data
        {
            "check_runs": [
                {"name": "lint", "conclusion": "failure"},
                {"name": "docs", "conclusion": "success"},
            ]
        },
    ]

    result = classify_pr_checks("owner", "repo", 999, "token")

    # Verify calls
    assert mock_fetch_json.call_count == 2  # noqa: PLR2004
    mock_fetch_json.assert_any_call("https://api.github.com/repos/owner/repo/pulls/999", "token")
    mock_fetch_json.assert_any_call(
        "https://api.github.com/repos/owner/repo/commits/mocksha123/check-runs", "token"
    )

    # Verify result
    assert "PR #999: mechanical lint failure; docs green" in result
    assert "safe follow-up patch recommended" in result


@patch("check_pr_lint_status.fetch_json")
def test_classify_pr_checks_no_sha(mock_fetch_json: MagicMock) -> None:
    """Test when SHA cannot be found."""
    mock_fetch_json.return_value = {"head": {}}
    result = classify_pr_checks("owner", "repo", 999, "token")
    assert result == "PR #999: Could not determine head SHA."
