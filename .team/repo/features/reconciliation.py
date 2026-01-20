"""Tracks reconciliation state to prevent loops."""

import json
from pathlib import Path
from datetime import datetime, timezone


class ReconciliationTracker:
    """Manages the state of reconciliation attempts per sprint."""

    def __init__(self, state_dir: Path | None = None):
        """Initialize the tracker.

        Args:
            state_dir: Directory to store state file. Defaults to .team/state
        """
        if state_dir:
            self.state_dir = state_dir
        else:
            # Default to .team/state relative to this file
            # This file is in .team/repo/reconciliation_tracker.py
            # So .parents[1] is .team/
            self.state_dir = Path(__file__).parents[1] / "state"

        self.state_file = self.state_dir / "reconciliation.json"
        self._ensure_state_dir()

    def _ensure_state_dir(self) -> None:
        """Ensure the state directory exists."""
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> dict:
        """Load state from file."""
        if not self.state_file.exists():
            return {}
        try:
            return json.loads(self.state_file.read_text())
        except json.JSONDecodeError:
            return {}

    def _save_state(self, state: dict) -> None:
        """Save state to file."""
        self.state_file.write_text(json.dumps(state, indent=2))

    def can_reconcile(self, sprint: int) -> bool:
        """Check if reconciliation is allowed for this sprint.

        We only allow one reconciliation attempt per sprint to avoid infinite loops.

        Args:
            sprint: The sprint number

        Returns:
            True if we can reconcile, False otherwise
        """
        state = self._load_state()
        sprint_str = str(sprint)

        # If no record for this sprint, we can reconcile
        if sprint_str not in state:
            return True

        # If we already reconciled this sprint, we cannot do it again
        return False

    def mark_reconciled(self, sprint: int, session_id: str) -> None:
        """Mark a sprint as having a reconciliation attempt.

        Args:
            sprint: The sprint number
            session_id: The session ID of the reconciliation attempt
        """
        state = self._load_state()
        state[str(sprint)] = {
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "attempted"
        }
        self._save_state(state)
