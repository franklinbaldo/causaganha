#!/bin/bash
# Monitor backfill health and send Telegram alerts if needed
#
# This script:
# 1. Runs health check (creates alert marker if issues found)
# 2. Checks for pending alerts
# 3. Sends alerts via OpenClaw if needed
#
# Usage:
#   ./scripts/monitoring/monitor_and_alert.sh [--dry-run] [--force]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Run health check
echo "Running backfill health check..."
cd "$PROJECT_ROOT"

# Use UV if available, otherwise fall back to system python
if command -v uv &> /dev/null; then
    PYTHON_CMD="uv run python"
else
    PYTHON_CMD="python3"
fi

# Run health check with any passed arguments
$PYTHON_CMD "$SCRIPT_DIR/check_backfill_health.py" "$@"
EXIT_CODE=$?

# Check for pending alerts
ALERT_MARKER="$SCRIPT_DIR/.pending_alert.json"

if [ -f "$ALERT_MARKER" ]; then
    echo ""
    echo "⚠️  Pending alert detected!"
    echo "Alert marker found at: $ALERT_MARKER"
    echo ""
    echo "To send this alert via Telegram, the OpenClaw main agent should run:"
    echo "  cd $PROJECT_ROOT"
    echo "  python scripts/monitoring/send_pending_alerts.py"
    echo ""
    echo "Or manually send using OpenClaw message tool with target: +556984186712"
    echo ""
fi

exit $EXIT_CODE
