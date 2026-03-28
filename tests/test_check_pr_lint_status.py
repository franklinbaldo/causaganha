from datetime import UTC, datetime, timedelta

from scripts.dev.check_pr_lint_status import calculate_urgency


def test_calculate_urgency_fresh():
    now = datetime.now(UTC)
    updated_at = now - timedelta(hours=5)
    updated_at_str = updated_at.isoformat()

    age, bucket = calculate_urgency(updated_at_str)
    assert age == 5
    assert bucket == "fresh"


def test_calculate_urgency_warning():
    now = datetime.now(UTC)
    updated_at = now - timedelta(hours=14)
    updated_at_str = updated_at.isoformat()

    age, bucket = calculate_urgency(updated_at_str)
    assert age == 14
    assert bucket == "warning"


def test_calculate_urgency_critical():
    now = datetime.now(UTC)
    updated_at = now - timedelta(hours=30)
    updated_at_str = updated_at.isoformat()

    age, bucket = calculate_urgency(updated_at_str)
    assert age == 30
    assert bucket == "critical"


def test_calculate_urgency_none():
    age, bucket = calculate_urgency(None)
    assert age == 0
    assert bucket == "fresh"


def test_calculate_urgency_invalid_date():
    age, bucket = calculate_urgency("invalid-date-format")
    assert age == 0
    assert bucket == "fresh"
