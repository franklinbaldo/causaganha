import re
from typing import Any, Dict, List, Optional
from repo.core.client import TeamClient

class EmailPoller:
    """Polls Jules session activities for new mail files and delivers them."""

    def __init__(self, client: TeamClient):
        self.client = client
        # Keep track of processed activities to avoid duplicate delivery
        # In a real system, we'd use persistent state or a timestamp filter
        self.processed_activity_names = set()

    def poll_and_deliver(self):
        """Main entry point for polling and delivering mail."""
        # 1. List all active sessions to monitor
        try:
            sessions_resp = self.client.list_sessions()
            sessions = sessions_resp.get("sessions", [])
        except Exception as e:
            print(f"Failed to list sessions: {e}")
            return

        # 2. For each session, check its activities
        for session in sessions:
            session_name = session["name"]
            try:
                activities_resp = self.client.get_activities(session_name)
                activities = activities_resp.get("activities", [])
            except Exception as e:
                print(f"Failed to get activities for {session_name}: {e}")
                continue

            for activity in activities:
                activity_name = activity["name"]
                if activity_name in self.processed_activity_names:
                    continue

                # 3. Inspect artifacts for mail patches
                for artifact in activity.get("artifacts", []):
                    contents = artifact.get("contents", {})
                    change_set = contents.get("changeSet", {})
                    git_patch = change_set.get("gitPatch", {})
                    unidiff = git_patch.get("unidiffPatch", "")

                    if not unidiff:
                        continue

                    # 4. Parse patch for added mail files
                    matches = self._find_mail_files(unidiff)
                    for recipient_id, email_content in matches:
                        self._deliver_to_recipient(recipient_id, email_content)

                self.processed_activity_names.add(activity_name)

    def _find_mail_files(self, patch: str) -> List[tuple[str, str]]:
        """Parses unidiff for files added to mail/new/ and extracts content."""
        results = []
        # Look for the start of a new file diff in the personas mail directory
        # Format: +++ b/.team/personas/<id>/mail/new/<filename>
        file_sep = re.compile(r"^\+\+\+ b/\.team/personas/([^/]+)/mail/new/.*$", re.MULTILINE)
        
        # Split patch into sections by file header
        sections = re.split(r"^(?=diff --git )", patch, flags=re.MULTILINE)
        
        for section in sections:
            match = file_sep.search(section)
            if match:
                recipient_id = match.group(1)
                # Extract the added lines (starting with +)
                # Skip the +++ line itself
                lines = []
                for line in section.splitlines():
                    if line.startswith("+") and not line.startswith("+++"):
                        lines.append(line[1:]) # Strip the leading +
                
                if lines:
                    email_content = "\n".join(lines)
                    results.append((recipient_id, email_content))
        
        return results

    def _deliver_to_recipient(self, recipient_id: str, email_content: str):
        """Finds the recipient's latest session and sends the email content."""
        print(f"Delivering mail to {recipient_id}...")
        try:
            sessions_resp = self.client.list_sessions()
            sessions = sessions_resp.get("sessions", [])
        except Exception as e:
            print(f"Failed to list sessions for delivery: {e}")
            return

        # Find latest session where title contains recipient_id
        # We look for "IN_PROGRESS" sessions first
        recipient_sessions = [
            s for s in sessions 
            if recipient_id.lower() in s.get("title", "").lower()
            and s.get("state") == "IN_PROGRESS"
        ]
        
        if not recipient_sessions:
            # Fallback to any state if no in-progess session found?
            recipient_sessions = [
                s for s in sessions 
                if recipient_id.lower() in s.get("title", "").lower()
            ]

        if not recipient_sessions:
            print(f"No active session found for {recipient_id}")
            return

        # Sort by createTime descending
        latest_session = sorted(recipient_sessions, key=lambda x: x.get("createTime", ""), reverse=True)[0]
        session_id = latest_session["name"].split("/")[-1]

        notification = f"""
## 📧 NEW EMAIL RECEIVED
You have received a new message via the system mail interface.

---
{email_content}
---

Please check your inbox (`my-tools email inbox`) and respond if needed.
"""
        try:
            self.client.send_message(session_id, notification)
            print(f"Successfully notified session {session_id}")
        except Exception as e:
            print(f"Failed to send message to {session_id}: {e}")
