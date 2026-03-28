import os
import sys


# Ensure scripts directory is in path for imports with hyphens in names
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import from generate-data.py
import importlib.util


spec = importlib.util.spec_from_file_location("generate_data", "scripts/dashboard/generate-data.py")
generate_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate_data)
classify_pr = generate_data.classify_pr

def test_classify_pr_pending():
    check_runs = [
        {"name": "tests", "status": "in_progress"}
    ]
    assert classify_pr(check_runs) == "pending"

def test_classify_pr_broken_core():
    check_runs = [
        {"name": "tests", "status": "completed", "conclusion": "failure"},
        {"name": "lint", "status": "completed", "conclusion": "success"}
    ]
    assert classify_pr(check_runs) == "broken"

def test_classify_pr_useful_but_lint_broken():
    check_runs = [
        {"name": "tests", "status": "completed", "conclusion": "success"},
        {"name": "docs", "status": "completed", "conclusion": "success"},
        {"name": "codeql", "status": "completed", "conclusion": "success"},
        {"name": "lint", "status": "completed", "conclusion": "failure"},
        {"name": "kilo code review", "status": "completed", "conclusion": "action_required"}
    ]
    assert classify_pr(check_runs) == "useful_but_lint_broken"

def test_classify_pr_useful_but_lint_broken_multiple():
    check_runs = [
        {"name": "tests", "status": "completed", "conclusion": "success"},
        {"name": "ruff", "status": "completed", "conclusion": "failure"},
        {"name": "format", "status": "completed", "conclusion": "failure"}
    ]
    assert classify_pr(check_runs) == "useful_but_lint_broken"

def test_classify_pr_ready_except_kilo():
    check_runs = [
        {"name": "tests", "status": "completed", "conclusion": "success"},
        {"name": "lint", "status": "completed", "conclusion": "success"},
        {"name": "kilo code review", "status": "completed", "conclusion": "action_required"}
    ]
    assert classify_pr(check_runs) == "ready_except_kilo"

def test_classify_pr_fully_ready():
    check_runs = [
        {"name": "tests", "status": "completed", "conclusion": "success"},
        {"name": "lint", "status": "completed", "conclusion": "success"},
        {"name": "kilo code review", "status": "completed", "conclusion": "success"}
    ]
    # In current implementation, fully ready falls through to "ready_except_kilo"
    # or fully green (which the dashboard treats similarly)
    assert classify_pr(check_runs) == "ready_except_kilo"

def test_classify_pr_unknown_failure_is_broken():
    check_runs = [
        {"name": "some random check", "status": "completed", "conclusion": "failure"},
        {"name": "lint", "status": "completed", "conclusion": "success"}
    ]
    assert classify_pr(check_runs) == "broken"

def test_classify_pr_mixed_failures_is_broken():
    check_runs = [
        {"name": "tests", "status": "completed", "conclusion": "failure"},
        {"name": "lint", "status": "completed", "conclusion": "failure"}
    ]
    # Core failure takes precedence over lint failure
    assert classify_pr(check_runs) == "broken"

def test_classify_pr_no_checks_is_pending():
    assert classify_pr([]) == "pending"

def test_classify_pr_cancelled_is_broken():
    check_runs = [
        {"name": "tests", "status": "completed", "conclusion": "cancelled"}
    ]
    assert classify_pr(check_runs) == "broken"
