"""Tests for verify_dashboard_status.py."""

from scripts.monitoring.verify_dashboard_status import analyze_html


TOTAL_TRIBUNALS = 91


def test_analyze_html_stale() -> None:
    """Test stale HTML."""
    with open("scripts/monitoring/tests/test_fallback.html") as f:
        html = f.read()
    result = analyze_html(html)
    assert result["status"] == "alive_but_stale_looking"
    assert result["healthy_tribunals"] == 0
    assert result["total_tribunals"] == TOTAL_TRIBUNALS
    assert result["last_collection"] == "--:--"
    assert result["global_eta"] == "Pending"


def test_analyze_html_healthy() -> None:
    """Test healthy HTML."""
    with open("scripts/monitoring/tests/test_healthy_fallback.html") as f:
        html = f.read()
    result = analyze_html(html)
    assert result["status"] == "advancing"
    assert result["healthy_tribunals"] == 50
    assert result["total_tribunals"] == TOTAL_TRIBUNALS
    assert result["last_collection"] == "14:30"
    assert result["global_eta"] == "~2 months"


def test_analyze_html_fetch_failed() -> None:
    """Test fetch failure."""
    result = analyze_html(None)
    assert result["status"] == "fetch_failed"


def test_analyze_html_invalid() -> None:
    """Test invalid HTML."""
    result = analyze_html("<html><body><h1>Hello World</h1></body></html>")
    assert result["status"] == "alive_but_stale_looking"
    assert result["healthy_tribunals"] == 0
    assert result["total_tribunals"] == TOTAL_TRIBUNALS
    assert result["last_collection"] == "--:--"
    assert result["global_eta"] == "Pending"


def test_analyze_html_alive_not_stale() -> None:
    """Test alive but not stale HTML."""
    result = analyze_html(
        "<html><title>Title</title><body><h1>1 of 91 tribunais saudáveis</h1>última coleta: --:--<br>"
        "Global ETA: Pending</body></html>"
    )
    assert result["status"] == "advancing"
    assert result["healthy_tribunals"] == 1
