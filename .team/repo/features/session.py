import json
import os
import uuid
import datetime
from pathlib import Path
from typing import List, Optional

SESSION_FILE = Path(".team/session.json")
PERSONAS_ROOT = Path(".team/personas")

class SessionManager:
    def __init__(self):
        self.session_data = self._load_session()

    def _load_session(self) -> dict:
        if SESSION_FILE.exists():
            try:
                return json.loads(SESSION_FILE.read_text())
            except Exception:
                pass
        return {}

    def _save_session(self):
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(json.dumps(self.session_data, indent=2))

    def validate_password(self, persona: str, password: str) -> bool:
        expected = str(uuid.uuid5(uuid.NAMESPACE_DNS, persona))
        return password == expected

    def login(self, persona: str, password: str, goals: List[str]):
        if not self.validate_password(persona, password):
            raise ValueError("Invalid password")
        
        # Capture current sequence during login
        sequence = "unknown"
        try:
            from repo.features.voting import VoteManager
            vm = VoteManager()
            sequence = vm.get_current_sequence(persona) or "unknown"
        except Exception:
            pass

        self.session_data = {
            "persona": persona,
            "sequence": sequence,
            "goals": goals,
            "start_time": datetime.datetime.now().isoformat(),
            "status": "active"
        }
        self._save_session()
        
        # Ensure persona directories exist
        (PERSONAS_ROOT / persona / "journals").mkdir(parents=True, exist_ok=True)
        (PERSONAS_ROOT / persona / "mail").mkdir(parents=True, exist_ok=True)

    def get_active_persona(self) -> Optional[str]:
        if self.session_data.get("status") == "active":
            return self.session_data.get("persona")
        return None

    def get_active_sequence(self) -> Optional[str]:
        if self.session_data.get("status") == "active":
            return self.session_data.get("sequence")
        return None

    def create_journal_entry(self, content: str, password: str):
        persona = self.get_active_persona()
        if not persona:
            raise RuntimeError("No active session. Please login first.")
        
        if not self.validate_password(persona, password):
            raise ValueError("Invalid password")
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
        filename = f"{timestamp}-Journal.md"
        path = PERSONAS_ROOT / persona / "journals" / filename
        
        goals = self.session_data.get("goals", [])
        goal_text = "\n".join([f"- {g}" for g in goals])
        
        full_content = f"""# Journal Entry: {timestamp}
## Goals
{goal_text}

## Execution
{content}
"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(full_content)
        return path

    def loop_break(self, reason: str):
        persona = self.get_active_persona()
        if not persona:
            raise RuntimeError("No active session.")
            
        self.session_data["status"] = "stopped"
        self.session_data["stop_reason"] = reason
        self._save_session()
        
        # Create artifact
        artifact_path = Path(".team/loop_break_context.json")
        artifact_path.write_text(json.dumps({
            "persona": persona,
            "reason": reason,
            "timestamp": datetime.datetime.now().isoformat(),
            "context": self.session_data
        }, indent=2))
        
        # Create STOP file
        (PERSONAS_ROOT / persona / "STOP").touch()

