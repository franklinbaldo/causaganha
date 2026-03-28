from scripts.dashboard.consecutive_failures import calculate_consecutive_failures


def test_no_failures() -> None:
    """Test when there are no failures."""
    runs = [
        {"conclusion": "success", "createdAt": "2024-01-02T00:00:00Z"},
        {"conclusion": "success", "createdAt": "2024-01-01T00:00:00Z"},
    ]
    failures, severity, url = calculate_consecutive_failures(runs)
    assert failures == 0
    assert severity is None
    assert url is None


def test_warning_failures() -> None:
    """Test warning severity."""
    runs = [
        {"conclusion": "failure", "createdAt": "2024-01-04T00:00:00Z", "url": "url3"},
        {"conclusion": "failure", "createdAt": "2024-01-03T00:00:00Z", "url": "url2"},
        {"conclusion": "failure", "createdAt": "2024-01-02T00:00:00Z", "url": "url1"},
        {"conclusion": "success", "createdAt": "2024-01-01T00:00:00Z", "url": "url0"},
    ]
    failures, severity, url = calculate_consecutive_failures(runs)
    expected_failures = 3
    assert failures == expected_failures
    assert severity == "warning"
    assert url == "url3"


def test_critical_failures() -> None:
    """Test critical severity."""
    runs = [
        {
            "conclusion": "timed_out",
            "createdAt": "2024-01-06T00:00:00Z",
            "html_url": "url5",
        },
        {"conclusion": "failure", "createdAt": "2024-01-05T00:00:00Z"},
        {"conclusion": "failure", "createdAt": "2024-01-04T00:00:00Z"},
        {"conclusion": "failure", "createdAt": "2024-01-03T00:00:00Z"},
        {"conclusion": "failure", "createdAt": "2024-01-02T00:00:00Z"},
        {"conclusion": "success", "createdAt": "2024-01-01T00:00:00Z"},
    ]
    failures, severity, url = calculate_consecutive_failures(runs)
    expected_failures = 5
    assert failures == expected_failures
    assert severity == "critical"
    assert url == "url5"


def test_mixed_failures_interrupted() -> None:
    """Test that a recent success resets the streak."""
    runs = [
        {"conclusion": "failure", "createdAt": "2024-01-03T00:00:00Z", "url": "url2"},
        {"conclusion": "success", "createdAt": "2024-01-02T00:00:00Z", "url": "url1"},
        {"conclusion": "failure", "createdAt": "2024-01-01T00:00:00Z", "url": "url0"},
    ]
    failures, severity, url = calculate_consecutive_failures(runs)
    expected_failures = 1
    assert failures == expected_failures
    assert severity is None
    assert url == "url2"
