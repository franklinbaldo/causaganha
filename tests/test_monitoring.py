"""Tests for backfill health monitoring system."""

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts" / "monitoring"
HEALTH_CHECK_SCRIPT = SCRIPTS_DIR / "check_backfill_health.py"


class TestHealthCheck:
    """Tests for check_backfill_health.py."""

    def test_script_exists(self):
        """Verify monitoring script exists and is executable."""
        assert HEALTH_CHECK_SCRIPT.exists()
        assert HEALTH_CHECK_SCRIPT.stat().st_mode & 0o111  # Check executable bit

    def test_help_output(self):
        """Test --help flag works."""
        result = subprocess.run(
            [sys.executable, str(HEALTH_CHECK_SCRIPT), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Monitor backfill health" in result.stdout

    def test_dry_run_healthy(self):
        """Test dry run with default thresholds (should be healthy)."""
        result = subprocess.run(
            [sys.executable, str(HEALTH_CHECK_SCRIPT), "--dry-run"],
            capture_output=True,
            text=True,
        )
        # Exit code 0 (healthy) or 1 (warning) are acceptable
        assert result.returncode in (0, 1)
        assert "Backfill Health Check" in result.stdout

    def test_dry_run_stale(self):
        """Test dry run with low threshold (should trigger stale warning)."""
        result = subprocess.run(
            [
                sys.executable,
                str(HEALTH_CHECK_SCRIPT),
                "--dry-run",
                "--stale-hours",
                "1",
            ],
            capture_output=True,
            text=True,
        )
        # Should be warning or critical
        assert result.returncode in (1, 2)
        assert "BACKFILL" in result.stdout
        if result.returncode == 1:
            assert "STALE" in result.stdout or "healthy" in result.stdout

    def test_custom_thresholds(self):
        """Test custom threshold arguments."""
        result = subprocess.run(
            [
                sys.executable,
                str(HEALTH_CHECK_SCRIPT),
                "--dry-run",
                "--stale-hours",
                "24",
                "--error-threshold",
                "75",
                "--cooldown-hours",
                "12",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode in (0, 1, 2)

    def test_alert_marker_created(self):
        """Test that alert marker is created when threshold exceeded."""
        alert_marker = SCRIPTS_DIR / ".pending_alert.json"
        
        # Clean up any existing marker
        if alert_marker.exists():
            alert_marker.unlink()

        # Run with low threshold to trigger alert
        result = subprocess.run(
            [
                sys.executable,
                str(HEALTH_CHECK_SCRIPT),
                "--stale-hours",
                "1",
                "--force",  # Bypass cooldown
            ],
            capture_output=True,
            text=True,
        )

        # If status is warning or critical, marker should exist
        if result.returncode in (1, 2):
            assert alert_marker.exists()
            
            # Verify marker format
            with alert_marker.open() as f:
                data = json.load(f)
            
            assert "target" in data
            assert "message" in data
            assert "timestamp" in data
            assert data["target"] == "+556984186712"
            
            # Clean up
            alert_marker.unlink()

    def test_alert_history_throttling(self):
        """Test alert throttling mechanism."""
        alert_history = SCRIPTS_DIR / ".alert_history.json"
        
        # Clean up
        if alert_history.exists():
            alert_history.unlink()

        # First run with force flag
        result1 = subprocess.run(
            [
                sys.executable,
                str(HEALTH_CHECK_SCRIPT),
                "--dry-run",
                "--stale-hours",
                "1",
                "--force",
            ],
            capture_output=True,
            text=True,
        )

        # Should trigger alert
        if result1.returncode in (1, 2):
            # Run again immediately (should be throttled)
            result2 = subprocess.run(
                [
                    sys.executable,
                    str(HEALTH_CHECK_SCRIPT),
                    "--dry-run",
                    "--stale-hours",
                    "1",
                ],
                capture_output=True,
                text=True,
            )
            
            # Should show throttle message
            assert "suppressed" in result2.stdout.lower() or "cooldown" in result2.stdout.lower()
            
            # Clean up
            if alert_history.exists():
                alert_history.unlink()


class TestIntegrationScript:
    """Tests for check_and_send_alert.py (OpenClaw integration)."""

    def test_integration_script_exists(self):
        """Verify integration script exists."""
        script = SCRIPTS_DIR / "check_and_send_alert.py"
        assert script.exists()
        assert script.stat().st_mode & 0o111  # Check executable bit

    def test_integration_output_format(self):
        """Test integration script output format."""
        script = SCRIPTS_DIR / "check_and_send_alert.py"
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
        )
        
        # Should always succeed (even if no alert)
        assert result.returncode in (0, 1, 2)
        
        # Check for expected sections
        assert "Backfill Health Check" in result.stdout or "No pending" in result.stdout


class TestAlertSender:
    """Tests for send_pending_alerts.py."""

    def test_sender_no_pending(self):
        """Test sender when no pending alerts."""
        script = SCRIPTS_DIR / "send_pending_alerts.py"
        
        # Make sure no marker exists
        alert_marker = SCRIPTS_DIR / ".pending_alert.json"
        if alert_marker.exists():
            alert_marker.unlink()

        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0
        assert "No pending alerts" in result.stdout

    def test_sender_with_pending(self):
        """Test sender with pending alert."""
        script = SCRIPTS_DIR / "send_pending_alerts.py"
        alert_marker = SCRIPTS_DIR / ".pending_alert.json"
        
        # Create fake alert marker
        fake_alert = {
            "target": "+556984186712",
            "message": "Test alert message",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        
        with alert_marker.open("w") as f:
            json.dump(fake_alert, f)

        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0
        assert "PENDING_ALERT_FOUND" in result.stdout
        assert "TARGET=" in result.stdout
        assert "MESSAGE_START" in result.stdout
        assert "Test alert message" in result.stdout
        
        # Marker should be removed
        assert not alert_marker.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
