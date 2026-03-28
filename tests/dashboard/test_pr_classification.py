"""Tests for PR classification logic."""

import importlib.util
import sys
from pathlib import Path


# Ensure scripts directory is in path for imports with hyphens in names
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Import from generate-data.py
spec = importlib.util.spec_from_file_location("generate_data", "scripts/dashboard/generate-data.py")
generate_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate_data)
classify_pr = generate_data.classify_pr


def test_classify_pr_pending() -> None:
    """Test that a PR with in-progress checks is classified as pending."""
    check_runs = [{"name": "tests", "status": "in_progress"}]
    assert classify_pr(check_runs) == "pending"  # noqa: S101


def test_classify_pr_broken_core() -> None:
    """Test that a PR with failing core tests is classified as broken."""
    check_runs = [
        {"name": "tests", "status": "completed", "conclusion": "failure"},
        {"name": "lint", "status": "completed", "conclusion": "success"},
    ]
    assert classify_pr(check_runs) == "broken"  # noqa: S101


def test_classify_pr_useful_but_lint_broken() -> None:
    """Test that a PR with only failing lint checks is classified as useful_but_lint_broken."""
    check_runs = [
        {"name": "tests", "status": "completed", "conclusion": "success"},
        {"name": "docs", "status": "completed", "conclusion": "success"},
        {"name": "codeql", "status": "completed", "conclusion": "success"},
        {"name": "lint", "status": "completed", "conclusion": "failure"},
        {"name": "kilo code review", "status": "completed", "conclusion": "action_required"},
    ]
    assert classify_pr(check_runs) == "useful_but_lint_broken"  # noqa: S101


def test_classify_pr_useful_but_lint_broken_multiple() -> None:
    """Test multiple failing formatting checks yield useful_but_lint_broken."""
    check_runs = [
        {"name": "tests", "status": "completed", "conclusion": "success"},
        {"name": "ruff", "status": "completed", "conclusion": "failure"},
        {"name": "format", "status": "completed", "conclusion": "failure"},
    ]
    assert classify_pr(check_runs) == "useful_but_lint_broken"  # noqa: S101


def test_classify_pr_ready_except_kilo() -> None:
    """Test that a PR fully ready except kilo code review is classified as ready_except_kilo."""
    check_runs = [
        {"name": "tests", "status": "completed", "conclusion": "success"},
        {"name": "lint", "status": "completed", "conclusion": "success"},
        {"name": "kilo code review", "status": "completed", "conclusion": "action_required"},
    ]
    assert classify_pr(check_runs) == "ready_except_kilo"  # noqa: S101


def test_classify_pr_fully_ready() -> None:
    """Test that a fully ready PR is mapped as ready_except_kilo (or ready)."""
    check_runs = [
        {"name": "tests", "status": "completed", "conclusion": "success"},
        {"name": "lint", "status": "completed", "conclusion": "success"},
        {"name": "kilo code review", "status": "completed", "conclusion": "success"},
    ]
    # In current implementation, fully ready falls through to "ready_except_kilo"
    # or fully green (which the dashboard treats similarly)
    assert classify_pr(check_runs) == "ready_except_kilo"  # noqa: S101


def test_classify_pr_unknown_failure_is_broken() -> None:
    """Test that a PR with an unknown failing check is classified as broken."""
    check_runs = [
        {"name": "some random check", "status": "completed", "conclusion": "failure"},
        {"name": "lint", "status": "completed", "conclusion": "success"},
    ]
    assert classify_pr(check_runs) == "broken"  # noqa: S101


def test_classify_pr_mixed_failures_is_broken() -> None:
    """Test that a PR with both core test failures and lint failures is classified as broken."""
    check_runs = [
        {"name": "tests", "status": "completed", "conclusion": "failure"},
        {"name": "lint", "status": "completed", "conclusion": "failure"},
    ]
    # Core failure takes precedence over lint failure
    assert classify_pr(check_runs) == "broken"  # noqa: S101


def test_classify_pr_no_checks_is_pending() -> None:
    """Test that a PR with no checks is classified as pending."""
    assert classify_pr([]) == "pending"  # noqa: S101


def test_classify_pr_cancelled_is_broken() -> None:
    """Test that a PR with a cancelled check is classified as broken."""
    check_runs = [{"name": "tests", "status": "completed", "conclusion": "cancelled"}]
    assert classify_pr(check_runs) == "broken"  # noqa: S101
