#!/usr/bin/env python3
"""Monitor GitHub Actions backfill progress.

Checks Internet Archive catalog for progress and alerts if stalled.
"""
import json
import sys
from datetime import datetime, timedelta, UTC
from pathlib import Path

import httpx


CATALOG_URL = "https://archive.org/download/causaganha-catalog/backfill-progress.json"
STATE_FILE = Path("memory/github-backfill-monitor.json")


def load_state() -> dict:
    """Load last known state."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "last_check": None,
        "last_progress_pct": 0.0,
        "last_items": 0,
        "last_change_at": None,
        "alerts_sent": 0,
    }


def save_state(state: dict):
    """Save current state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def fetch_progress() -> dict | None:
    """Fetch current backfill progress from IA."""
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(CATALOG_URL)
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"❌ Error fetching progress: {e}", file=sys.stderr)
    return None


def check_stall(state: dict, current: dict, stall_threshold_minutes: int = 60) -> tuple[bool, str]:
    """Check if backfill is stalled.
    
    Returns (is_stalled, message).
    """
    now = datetime.now(UTC).isoformat()
    
    current_pct = current.get("progress_pct", 0)
    current_items = current.get("items_collected", 0)
    
    # First run - record baseline
    if state["last_change_at"] is None:
        state["last_progress_pct"] = current_pct
        state["last_items"] = current_items
        state["last_change_at"] = now
        state["last_check"] = now
        return False, "✅ Baseline recorded"
    
    # Check if progress changed
    progress_changed = (
        current_pct > state["last_progress_pct"]
        or current_items > state["last_items"]
    )
    
    if progress_changed:
        state["last_progress_pct"] = current_pct
        state["last_items"] = current_items
        state["last_change_at"] = now
        state["last_check"] = now
        state["alerts_sent"] = 0  # Reset alert counter
        return False, f"✅ Progress: {current_pct:.2f}% ({current_items} items)"
    
    # No progress - check if stalled
    last_change = datetime.fromisoformat(state["last_change_at"])
    elapsed = (datetime.now(UTC) - last_change).total_seconds() / 60
    
    state["last_check"] = now
    
    if elapsed > stall_threshold_minutes:
        state["alerts_sent"] += 1
        return True, (
            f"🚨 STALLED: No progress for {elapsed:.0f} minutes\n"
            f"   Last: {current_pct:.2f}% ({current_items} items)\n"
            f"   Alert #{state['alerts_sent']}"
        )
    
    return False, f"⏳ No progress for {elapsed:.0f}min (threshold: {stall_threshold_minutes}min)"


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor GitHub Actions backfill")
    parser.add_argument(
        "--stall-threshold",
        type=int,
        default=60,
        help="Minutes without progress before alerting (default: 60)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON for scripting",
    )
    args = parser.parse_args()
    
    state = load_state()
    current = fetch_progress()
    
    if current is None:
        print("❌ Could not fetch progress from IA", file=sys.stderr)
        return 1
    
    is_stalled, message = check_stall(state, current, args.stall_threshold)
    save_state(state)
    
    if args.json:
        print(json.dumps({
            "stalled": is_stalled,
            "message": message,
            "current_pct": current.get("progress_pct", 0),
            "current_items": current.get("items_collected", 0),
            "last_change_at": state["last_change_at"],
            "alerts_sent": state["alerts_sent"],
        }))
    else:
        print(message)
    
    return 1 if is_stalled else 0


if __name__ == "__main__":
    sys.exit(main())
