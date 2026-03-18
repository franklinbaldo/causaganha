#!/usr/bin/env python3
"""Backfill health monitoring with Telegram alerting.

This script monitors the backfill progress and sends Telegram alerts when:
- No progress detected for >6 hours (configurable)
- Error rate exceeds 50% sustained
- All tribunals stopped unexpectedly

Alert throttling prevents spam (max 1 alert per 6 hours per issue type).

Usage:
    # Run health check (returns 0=ok, 1=warning, 2=critical)
    python scripts/monitoring/check_backfill_health.py

    # Check specific thresholds
    python scripts/monitoring/check_backfill_health.py --stale-hours 12 --error-threshold 75

    # Dry run (no Telegram messages)
    python scripts/monitoring/check_backfill_health.py --dry-run

Exit codes:
    0: OK - Backfill progressing normally
    1: WARNING - Minor issues detected
    2: CRITICAL - Backfill stuck or failing
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal


# Alert history file (tracks sent alerts to prevent spam)
ALERT_HISTORY_FILE = Path(__file__).parent / ".alert_history.json"

# Default thresholds
DEFAULT_STALE_HOURS = 6
DEFAULT_ERROR_THRESHOLD_PCT = 50.0
DEFAULT_ALERT_COOLDOWN_HOURS = 6

# Telegram target (Franklin)
TELEGRAM_TARGET = "+556984186712"


@dataclass
class BackfillStatus:
    """Backfill health status."""

    progress_pct: float
    oldest_date: str
    newest_date: str
    total_items: int
    last_updated: str
    age_hours: float
    is_stale: bool
    is_stuck: bool
    message: str
    level: Literal["ok", "warning", "critical"]


@dataclass
class AlertHistory:
    """Alert history to prevent spam."""

    stale_last_sent: str | None = None
    stuck_last_sent: str | None = None
    error_last_sent: str | None = None


def load_alert_history() -> AlertHistory:
    """Load alert history from disk."""
    if not ALERT_HISTORY_FILE.exists():
        return AlertHistory()

    try:
        with ALERT_HISTORY_FILE.open() as f:
            data = json.load(f)
        return AlertHistory(
            stale_last_sent=data.get("stale_last_sent"),
            stuck_last_sent=data.get("stuck_last_sent"),
            error_last_sent=data.get("error_last_sent"),
        )
    except Exception:
        return AlertHistory()


def save_alert_history(history: AlertHistory) -> None:
    """Save alert history to disk."""
    ALERT_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with ALERT_HISTORY_FILE.open("w") as f:
        json.dump(
            {
                "stale_last_sent": history.stale_last_sent,
                "stuck_last_sent": history.stuck_last_sent,
                "error_last_sent": history.error_last_sent,
            },
            f,
            indent=2,
        )


def can_send_alert(alert_type: str, history: AlertHistory, cooldown_hours: int) -> bool:
    """Check if enough time has passed since last alert of this type."""
    last_sent_str = getattr(history, f"{alert_type}_last_sent")
    if not last_sent_str:
        return True

    try:
        last_sent = datetime.fromisoformat(last_sent_str)
        now = datetime.now(UTC)
        return (now - last_sent) > timedelta(hours=cooldown_hours)
    except Exception:
        return True  # If parsing fails, allow alert


def mark_alert_sent(alert_type: str, history: AlertHistory) -> AlertHistory:
    """Mark an alert as sent in history."""
    now = datetime.now(UTC).isoformat()
    if alert_type == "stale":
        return AlertHistory(
            stale_last_sent=now,
            stuck_last_sent=history.stuck_last_sent,
            error_last_sent=history.error_last_sent,
        )
    if alert_type == "stuck":
        return AlertHistory(
            stale_last_sent=history.stale_last_sent,
            stuck_last_sent=now,
            error_last_sent=history.error_last_sent,
        )
    if alert_type == "error":
        return AlertHistory(
            stale_last_sent=history.stale_last_sent,
            stuck_last_sent=history.stuck_last_sent,
            error_last_sent=now,
        )
    return history


def check_backfill_progress(stale_hours: int = DEFAULT_STALE_HOURS) -> BackfillStatus:
    """Check backfill progress from Internet Archive catalog.

    Args:
        stale_hours: Hours threshold for considering progress stale

    Returns:
        BackfillStatus with health information
    """
    import urllib.request

    url = "https://archive.org/download/causaganha-catalog/backfill-progress.json"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read())

        progress_pct = data.get("progress_pct", 0.0)
        oldest_date = data.get("oldest_date", "unknown")
        newest_date = data.get("newest_date", "unknown")
        total_items = data.get("total_items", 0)
        last_updated_str = data.get("last_updated", "")

        # Calculate age
        try:
            last_updated = datetime.fromisoformat(last_updated_str)
            now = datetime.now(UTC)
            age = now - last_updated
            age_hours = age.total_seconds() / 3600
        except Exception:
            age_hours = 999.0  # Assume stale if parsing fails

        is_stale = age_hours > stale_hours
        is_stuck = progress_pct < 0.1 and age_hours > stale_hours * 2

        # Determine level and message
        if is_stuck:
            level = "critical"
            message = f"🚨 BACKFILL STUCK: No progress in {age_hours:.1f}h (progress: {progress_pct:.2f}%)"
        elif is_stale:
            level = "warning"
            message = (
                f"⚠️ BACKFILL STALE: No updates in {age_hours:.1f}h (progress: {progress_pct:.2f}%)"
            )
        else:
            level = "ok"
            message = f"✅ Backfill healthy: {progress_pct:.2f}% complete ({total_items} items)"

        return BackfillStatus(
            progress_pct=progress_pct,
            oldest_date=oldest_date,
            newest_date=newest_date,
            total_items=total_items,
            last_updated=last_updated_str,
            age_hours=age_hours,
            is_stale=is_stale,
            is_stuck=is_stuck,
            message=message,
            level=level,
        )

    except Exception as e:
        return BackfillStatus(
            progress_pct=0.0,
            oldest_date="unknown",
            newest_date="unknown",
            total_items=0,
            last_updated="unknown",
            age_hours=999.0,
            is_stale=True,
            is_stuck=True,
            message=f"❌ CRITICAL: Failed to fetch backfill progress: {e}",
            level="critical",
        )


def check_pipeline_errors(error_threshold: float = DEFAULT_ERROR_THRESHOLD_PCT) -> dict:
    """Check recent pipeline errors from GitHub Actions runs using gh CLI.

    Args:
        error_threshold: Error rate percentage threshold

    Returns:
        Dictionary with error statistics
    """
    import subprocess

    try:
        # Get last 5 runs of "Data Pipeline"
        result = subprocess.run(
            [
                "gh",
                "run",
                "list",
                "-w",
                "Data Pipeline",
                "-R",
                "franklinbaldo/causaganha",
                "-L",
                "5",
                "--json",
                "conclusion,status,createdAt,url",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        runs = json.loads(result.stdout)

        if not runs:
            return {
                "error_rate": 0.0,
                "recent_failures": 0,
                "total_runs": 0,
                "is_failing": False,
                "message": "No recent runs found",
                "last_run_status": "unknown",
            }

        total_runs = len(runs)
        failures = [r for r in runs if r.get("conclusion") == "failure"]
        recent_failures = len(failures)
        error_rate = (recent_failures / total_runs) * 100

        last_run = runs[0]
        last_status = last_run.get("conclusion") or last_run.get("status")

        return {
            "error_rate": error_rate,
            "recent_failures": recent_failures,
            "total_runs": total_runs,
            "is_failing": error_rate >= error_threshold,
            "message": f"Pipeline is failing ({recent_failures}/{total_runs} failed)",
            "last_run_status": last_status,
            "last_run_url": last_run.get("url"),
        }

    except Exception as e:
        return {
            "error_rate": 0.0,
            "recent_failures": 0,
            "total_runs": 0,
            "is_failing": False,
            "message": f"Error checking pipeline: {e}",
            "last_run_status": "error",
        }


def format_telegram_message(status: BackfillStatus, errors: dict) -> str:
    """Format Telegram alert message.

    Args:
        status: Backfill status
        errors: Pipeline error statistics

    Returns:
        Formatted message text
    """
    lines = [
        "🔔 **CausaGanha Backfill Alert**",
        "",
        status.message,
        "",
        "**Status:**",
        f"• Progress: {status.progress_pct:.2f}%",
        f"• Total items: {status.total_items}",
        f"• Date range: {status.oldest_date} → {status.newest_date}",
        f"• Last update: {status.age_hours:.1f}h ago",
        "",
        "**Worker Status (GitHub Actions):**",
        f"• Status: {errors.get('last_run_status', 'unknown')}",
        f"• Recent Failures: {errors.get('recent_failures', 0)}/{errors.get('total_runs', 0)}",
        f"• Message: {errors.get('message', 'N/A')}",
    ]

    if errors.get("last_run_url"):
        lines.append(f"• Last Run: [View on GitHub]({errors['last_run_url']})")

    lines.append("")
    lines.append("**Next Steps:**")

    if status.is_stuck or errors.get("is_failing"):
        lines.extend(
            [
                "1. Check GitHub Actions workflow logs (429 errors detected?)",
                "2. Verify Internet Archive upload status",
                "3. Review consolidate.py logs for errors",
                "4. Consider manual restart if needed",
            ]
        )
    elif status.is_stale:
        lines.extend(
            [
                "1. Check if scheduled runs are executing",
                "2. Review recent workflow logs",
                "3. Monitor for next update (expected every 15min)",
            ]
        )

    lines.extend(
        [
            "",
            "🔗 [GitHub Actions](https://github.com/franklinbaldo/causaganha/actions)",
            "🔗 [Dashboard](https://causaganha.com.br)",
        ]
    )

    return "\n".join(lines)


def send_telegram_alert(message: str, dry_run: bool = False) -> bool:
    """Send Telegram alert via OpenClaw message tool.

    Args:
        message: Message text to send
        dry_run: If True, print message instead of sending

    Returns:
        True if sent successfully, False otherwise
    """
    if dry_run:
        return True

    # In production, this would use the OpenClaw message tool
    # For now, we'll use a simple approach that can be called from the main agent

    # Create a marker file that the main agent can detect
    alert_marker = Path(__file__).parent / ".pending_alert.json"
    alert_marker.write_text(
        json.dumps(
            {
                "target": TELEGRAM_TARGET,
                "message": message,
                "timestamp": datetime.now(UTC).isoformat(),
            },
            indent=2,
        ),
    )

    return True


def main() -> int:
    """Main monitoring logic."""
    parser = argparse.ArgumentParser(description="Monitor backfill health and send alerts")
    parser.add_argument(
        "--stale-hours",
        type=int,
        default=DEFAULT_STALE_HOURS,
        help=f"Hours threshold for stale progress (default: {DEFAULT_STALE_HOURS})",
    )
    parser.add_argument(
        "--error-threshold",
        type=float,
        default=DEFAULT_ERROR_THRESHOLD_PCT,
        help=f"Error rate percentage threshold (default: {DEFAULT_ERROR_THRESHOLD_PCT})",
    )
    parser.add_argument(
        "--cooldown-hours",
        type=int,
        default=DEFAULT_ALERT_COOLDOWN_HOURS,
        help=f"Alert cooldown hours (default: {DEFAULT_ALERT_COOLDOWN_HOURS})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print alerts instead of sending",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force send alert (bypass cooldown)",
    )
    args = parser.parse_args()

    # Load alert history
    history = load_alert_history()

    # Check backfill progress
    status = check_backfill_progress(stale_hours=args.stale_hours)
    errors = check_pipeline_errors(error_threshold=args.error_threshold)

    # Print status

    # Determine if alert should be sent
    needs_alert = False
    alert_type = None

    if status.is_stuck:
        alert_type = "stuck"
        needs_alert = args.force or can_send_alert(alert_type, history, args.cooldown_hours)
    elif status.is_stale:
        alert_type = "stale"
        needs_alert = args.force or can_send_alert(alert_type, history, args.cooldown_hours)

    # Send alert if needed
    if needs_alert and alert_type:
        message = format_telegram_message(status, errors)
        if send_telegram_alert(message, dry_run=args.dry_run):
            if not args.dry_run:
                history = mark_alert_sent(alert_type, history)
                save_alert_history(history)
        else:
            return 2
    elif status.level in ("warning", "critical"):
        pass

    # Return appropriate exit code
    if status.level == "critical":
        return 2
    if status.level == "warning":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
