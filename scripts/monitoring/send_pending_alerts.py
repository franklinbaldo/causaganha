#!/usr/bin/env python3
"""Send pending Telegram alerts created by check_backfill_health.py.

This script is called by the OpenClaw main agent to send alerts via the message tool.
The monitoring script creates alert markers, and this script sends them.

Usage:
    # Called from OpenClaw agent context (has access to message tool)
    python scripts/monitoring/send_pending_alerts.py
"""

import json
import sys
from pathlib import Path


def main() -> int:
    """Check for pending alerts and return info for agent to send."""
    alert_marker = Path(__file__).parent / ".pending_alert.json"

    if not alert_marker.exists():
        print("No pending alerts")
        return 0

    try:
        with alert_marker.open() as f:
            alert_data = json.load(f)

        # Print alert info in a format the agent can parse
        print("PENDING_ALERT_FOUND")
        print(f"TARGET={alert_data['target']}")
        print(f"TIMESTAMP={alert_data['timestamp']}")
        print("MESSAGE_START")
        print(alert_data['message'])
        print("MESSAGE_END")

        # Remove marker after reading
        alert_marker.unlink()

        return 0

    except Exception as e:
        print(f"Error reading alert marker: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
