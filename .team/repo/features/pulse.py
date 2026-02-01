import csv
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from repo.features.mail import list_inbox

SCHEDULE_FILE = Path(".team/schedule.csv")
TASKS_TODO_DIR = Path(".team/tasks/todo")
LOG_FILE = Path(".team/tools_use.csv")  # Legacy
LOGS_DIR = Path(".team/logs/tools_use")  # New per-session logs

class PulseManager:
    def get_sitrep(self, persona_id: str, current_sequence: Optional[str]) -> Dict[str, Any]:
        """
        Gathers all data for a persona's situation report.
        """
        sitrep = {
            "persona": persona_id,
            "sequence": current_sequence or "unknown",
            "next_persona": self._get_next_persona(current_sequence),
            "unread_mail_count": self._get_unread_mail_count(persona_id),
            "pending_tasks": self._get_pending_tasks(limit=3),
            "last_tool_used": self._get_last_tool_used(persona_id)
        }
        return sitrep

    def _get_next_persona(self, current_sequence: Optional[str]) -> str:
        if not current_sequence or not SCHEDULE_FILE.exists():
            return "unknown"
        
        try:
            with open(SCHEDULE_FILE, mode='r', newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                for i, row in enumerate(rows):
                    if row['sequence'] == current_sequence:
                        if i + 1 < len(rows):
                            next_row = rows[i+1]
                            return f"{next_row['sequence']} ({next_row['persona']})"
        except Exception:
            pass
        return "none scheduled"

    def _get_unread_mail_count(self, persona_id: str) -> int:
        try:
            # We use the existing mail feature logic
            messages = list_inbox(persona_id, unread_only=True)
            return len(messages)
        except Exception:
            return 0

    def _get_pending_tasks(self, limit: int = 3) -> List[str]:
        if not TASKS_TODO_DIR.exists():
            return []

        try:
            tasks = []
            # List .md files in todo dir, excluding TEMPLATE.md
            for f in sorted(TASKS_TODO_DIR.glob("*.md"), reverse=True):
                if f.name == "TEMPLATE.md":
                    continue
                # Simple heuristic: older files might be higher priority?
                # Or just use filenames which often have timestamps.
                tasks.append(f.stem)
                if len(tasks) >= limit:
                    break
            return tasks
        except Exception:
            return []

    def _get_last_tool_used(self, persona_id: str) -> str:
        """
        Get the last tool used by a persona, scanning per-session log files.

        Checks both new per-session logs (.team/logs/tools_use/{persona}_*.csv)
        and legacy single log file (.team/tools_use.csv).
        """
        all_rows = []

        # Read from new per-session logs
        if LOGS_DIR.exists():
            try:
                # Find all log files for this persona
                pattern = f"{persona_id}_*.csv"
                for log_file in LOGS_DIR.glob(pattern):
                    try:
                        with open(log_file, mode='r', newline='') as f:
                            reader = csv.DictReader(f)
                            all_rows.extend(list(reader))
                    except Exception:
                        continue  # Skip corrupted files
            except Exception:
                pass

        # Fallback to legacy log file if exists
        if LOG_FILE.exists():
            try:
                with open(LOG_FILE, mode='r', newline='') as f:
                    reader = csv.DictReader(f)
                    rows = [row for row in reader if row.get('persona') == persona_id]
                    all_rows.extend(rows)
            except Exception:
                pass

        # Sort by timestamp (most recent first) and find last non-login command
        try:
            all_rows.sort(key=lambda r: r.get('timestamp', ''), reverse=True)
            for row in all_rows:
                cmd = row.get('command', '')
                if "login" in cmd.lower():
                    continue
                return cmd
        except Exception:
            pass

        return "none"

    def format_sitrep(self, sitrep: Dict[str, Any]) -> str:
        """
        Formats the sitrep data into a beautiful Rich/String display.
        """
        output = []
        output.append("📡 [bold cyan]SITUATION REPORT (SITREP)[/bold cyan]")
        output.append(f"👤 Persona: [green]{sitrep['persona']}[/green]")
        output.append(f"🔢 Sequence: [yellow]{sitrep['sequence']}[/yellow] (Next: {sitrep['next_persona']})")

        mail_color = "red" if sitrep['unread_mail_count'] > 0 else "green"
        output.append(f"📧 Mail: [{mail_color}]{sitrep['unread_mail_count']} unread[/{mail_color}]")

        if sitrep['pending_tasks']:
            output.append("📋 Pending Tasks (Top 3):")
            for task in sitrep['pending_tasks']:
                output.append(f"  - {task}")
        else:
            output.append("📋 Pending Tasks: [green]Clean list![/green]")

        output.append(f"🛠️  Last Tool: [dim]{sitrep['last_tool_used']}[/dim]")

        return "\n".join(output)
