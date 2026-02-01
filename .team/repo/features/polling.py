import re
from typing import Any

from repo.core.client import TeamClient


def get_latest_activity_timestamp(activities: list[dict[str, Any]]) -> str | None:
    """Extract the latest createTime from a list of activities.

    Args:
        activities: List of activity dicts from Jules API.

    Returns:
        The latest RFC 3339 timestamp, or None if no activities.

    """
    if not activities:
        return None

    timestamps = [a.get("createTime") for a in activities if a.get("createTime")]
    if not timestamps:
        return None

    # Return the max timestamp (latest)
    return max(timestamps)


class EmailPoller:
    """Polls Jules session activities for new mail files and delivers them.

    Uses the createTime filter (Jules API Jan 2026) for efficient incremental
    polling instead of tracking processed activity names in memory.
    """

    def __init__(self, client: TeamClient):
        self.client = client
        # Track last poll timestamp per session for incremental polling
        # Key: session_id, Value: RFC 3339 timestamp of last seen activity
        self.last_poll_times: dict[str, str] = {}

    def poll_and_deliver(self):
        """Main entry point for polling and delivering mail.

        Uses createTime filtering to only fetch activities since last poll,
        reducing API overhead and network traffic.
        """
        # 1. List all active sessions to monitor
        try:
            sessions_resp = self.client.list_sessions()
            sessions = sessions_resp.get("sessions", [])
        except Exception as e:
            print(f"Failed to list sessions: {e}")
            return

        # 2. For each session, check its activities (with timestamp filtering)
        for session in sessions:
            session_name = session["name"]
            session_id = session_name.split("/")[-1]

            # Get last poll timestamp for this session (if any)
            create_time_after = self.last_poll_times.get(session_id)

            try:
                activities_resp = self.client.get_activities(
                    session_name,
                    create_time_after=create_time_after,
                )
                activities = activities_resp.get("activities", [])
            except Exception as e:
                print(f"Failed to get activities for {session_name}: {e}")
                continue

            # Skip if no new activities
            if not activities:
                continue

            # Process all activities (they're all new since we filtered)
            for activity in activities:
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

            # Update last poll timestamp with the latest activity time
            latest_timestamp = get_latest_activity_timestamp(activities)
            if latest_timestamp:
                self.last_poll_times[session_id] = latest_timestamp

    def _find_mail_files(self, patch: str) -> list[tuple[str, str]]:
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
