#!/usr/bin/env python3
"""OpenClaw agent integration for backfill monitoring.

This script is designed to be called from the OpenClaw agent heartbeat.
It checks backfill health and outputs instructions for sending Telegram alerts.

Usage (from OpenClaw agent):
    result = exec("cd /path/to/causaganha && python3 scripts/monitoring/check_and_send_alert.py")
    if "SEND_TELEGRAM_ALERT" in result:
        # Parse message and send via message tool
"""

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Run health check and output alert if needed."""
    script_dir = Path(__file__).parent
    health_check = script_dir / "check_backfill_health.py"

    # Run health check
    result = subprocess.run(
        [sys.executable, str(health_check)],
        capture_output=True,
        text=True,
    )

    # Print health check output
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # Check for pending alert
    alert_marker = script_dir / ".pending_alert.json"
    if alert_marker.exists():
        try:
            with alert_marker.open() as f:
                alert_data = json.load(f)

            # Output alert in format OpenClaw agent can parse
            print("\n" + "=" * 60)
            print("SEND_TELEGRAM_ALERT")
            print(f"TARGET: {alert_data['target']}")
            print(f"TIMESTAMP: {alert_data['timestamp']}")
            print("MESSAGE:")
            print(alert_data["message"])
            print("=" * 60)

            # Remove marker after reading
            alert_marker.unlink()

        except Exception as e:
            print(f"Error reading alert marker: {e}", file=sys.stderr)
            return 1

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
