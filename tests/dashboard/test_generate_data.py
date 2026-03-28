import pytest
import sys
import os
import importlib.util

# Load module dynamically because its name has a hyphen
module_name = 'generate_data'
module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts/dashboard/generate-data.py'))

spec = importlib.util.spec_from_file_location(module_name, module_path)
generate_data = importlib.util.module_from_spec(spec)
sys.modules[module_name] = generate_data
spec.loader.exec_module(generate_data)

calculate_recent_failure_rate = generate_data.calculate_recent_failure_rate

def test_calculate_recent_failure_rate_empty():
    """Test with empty runs list."""
    result = calculate_recent_failure_rate([])
    assert result == {
        "recent_failed_count": 0,
        "recent_window_size": 0,
        "recent_failure_rate": 0.0,
        "latest_failed_run_url": None,
    }

def test_calculate_recent_failure_rate_100_percent_failure():
    """Test the scenario where all runs in the recent window have failed (real current case)."""
    runs = [
        {"conclusion": "failure", "createdAt": "2026-01-24T18:09:08Z", "url": "url1"},
        {"conclusion": "timed_out", "createdAt": "2026-01-24T17:59:40Z", "url": "url2"},
        {"conclusion": "failure", "createdAt": "2026-01-24T17:58:17Z", "url": "url3"},
        {"conclusion": "failure", "createdAt": "2026-01-23T17:58:17Z", "url": "url4"},
    ]

    # Using window_size=3
    result = calculate_recent_failure_rate(runs, window_size=3)

    # We expect the 3 most recent (url1, url2, url3) to be selected. All 3 failed.
    assert result["recent_failed_count"] == 3
    assert result["recent_window_size"] == 3
    assert result["recent_failure_rate"] == 100.0
    assert result["latest_failed_run_url"] == "url1"

def test_calculate_recent_failure_rate_partial_failure():
    """Test with a mix of success and failure."""
    runs = [
        {"conclusion": "success", "createdAt": "2026-01-24T18:09:08Z", "url": "url1"},
        {"conclusion": "failure", "createdAt": "2026-01-24T17:59:40Z", "url": "url2"},
        {"conclusion": "success", "createdAt": "2026-01-24T17:58:17Z", "url": "url3"},
        {"conclusion": "timed_out", "createdAt": "2026-01-23T17:58:17Z", "url": "url4"},
    ]

    # Using window_size=4
    result = calculate_recent_failure_rate(runs, window_size=4)

    assert result["recent_failed_count"] == 2
    assert result["recent_window_size"] == 4
    assert result["recent_failure_rate"] == 50.0
    assert result["latest_failed_run_url"] == "url2"

def test_calculate_recent_failure_rate_no_failures():
    """Test where all runs are successful."""
    runs = [
        {"conclusion": "success", "createdAt": "2026-01-24T18:09:08Z", "url": "url1"},
        {"conclusion": "success", "createdAt": "2026-01-24T17:59:40Z", "url": "url2"},
    ]

    result = calculate_recent_failure_rate(runs, window_size=2)

    assert result["recent_failed_count"] == 0
    assert result["recent_window_size"] == 2
    assert result["recent_failure_rate"] == 0.0
    assert result["latest_failed_run_url"] is None

def test_calculate_recent_failure_rate_small_window():
    """Test where fewer runs exist than the window size."""
    runs = [
        {"conclusion": "failure", "createdAt": "2026-01-24T18:09:08Z", "url": "url1"},
        {"conclusion": "success", "createdAt": "2026-01-24T17:59:40Z", "url": "url2"},
    ]

    # Requesting window_size=8, but only 2 runs exist
    result = calculate_recent_failure_rate(runs, window_size=8)

    assert result["recent_failed_count"] == 1
    assert result["recent_window_size"] == 2
    assert result["recent_failure_rate"] == 50.0
    assert result["latest_failed_run_url"] == "url1"
