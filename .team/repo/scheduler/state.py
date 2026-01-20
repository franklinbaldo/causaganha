import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, BeforeValidator
from typing_extensions import Annotated


# Custom type for history keys to ensure they are strings of integers
HistoryKey = Annotated[str, BeforeValidator(lambda x: str(int(x)))]


class TrackState(BaseModel):
    """State for a single execution track."""
    persona_id: Optional[str] = None
    session_id: Optional[str] = None
    pr_number: Optional[int] = None
    updated_at: Optional[datetime] = None

    @property
    def last_persona_id(self) -> Optional[str]:
        return self.persona_id

    @property
    def last_session_id(self) -> Optional[str]:
        return self.session_id

    @property
    def last_pr_number(self) -> Optional[int]:
        return self.pr_number


class PersistentCycleState(BaseModel):
    """Persistent state for the cycle scheduler.
    
    Supports both legacy single-cycle history and new multi-track state.
    """

    history: Dict[HistoryKey, Dict[str, Any]] = Field(default_factory=dict)
    tracks: Dict[str, TrackState] = Field(default_factory=dict)

    @property
    def sorted_history_keys(self) -> List[str]:
        """Get history keys sorted as integers in descending order."""
        return sorted(self.history.keys(), key=lambda x: int(x), reverse=True)

    @property
    def persona_id(self) -> Optional[str]:
        """Get the persona ID from the most recent session (Legacy/Default)."""
        keys = self.sorted_history_keys
        return self.history[keys[0]].get("persona_id") if keys else None

    @property
    def session_id(self) -> Optional[str]:
        """Get the session ID from the most recent session (Legacy/Default)."""
        keys = self.sorted_history_keys
        return self.history[keys[0]].get("session_id") if keys else None

    @property
    def pr_number(self) -> Optional[int]:
        """Get the PR number from the most recent session (Legacy/Default)."""
        keys = self.sorted_history_keys
        return self.history[keys[0]].get("pr_number") if keys else None

    def get_track(self, track_name: str) -> TrackState:
        """Get state for a specific track, initializing if needed."""
        if track_name not in self.tracks:
            self.tracks[track_name] = TrackState()
        return self.tracks[track_name]

    @classmethod
    def load(cls, path: Path) -> "PersistentCycleState":
        """Load state from JSON file."""
        if not path.exists():
            return cls()

        try:
            with open(path) as f:
                data = json.load(f)
            
            # Handle legacy list history format
            if isinstance(data, dict) and isinstance(data.get("history"), list):
                history_list = data.pop("history")
                # Convert legacy list history to dict
                # In legacy list, history[0] was the latest.
                # We want history["0"] to be the oldest for sequential growth.
                data["history"] = {str(i): entry for i, entry in enumerate(reversed(history_list))}
            elif isinstance(data, list):
                # Convert legacy list-only format to dict
                data = {"history": {str(i): entry for i, entry in enumerate(reversed(data))}}

            # Handle legacy \'last_\' prefix in track data if necessary
            if isinstance(data, dict) and "tracks" in data:
                new_tracks = {}
                for name, t_data in data["tracks"].items():
                    clean_data = {}
                    for k, v in t_data.items():
                        new_k = k.replace("last_", "")
                        clean_data[new_k] = v
                    new_tracks[name] = clean_data
                data["tracks"] = new_tracks

            return cls.model_validate(data)
        except Exception:
            return cls()

    def save(self, path: Path) -> None:
        """Save state to JSON file."""
        data = self.model_dump(mode='json')
        # Ensure history is sorted by keys as integers before saving
        # The model_dump already converts datetimes to strings
        sorted_history_json = {
            k: data["history"][k]
            for k in sorted(data["history"].keys(), key=lambda x: int(x))
        }
        data["history"] = sorted_history_json

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def record_session(
        self,
        persona_id: str,
        persona_index: int,
        session_id: str,
        pr_number: Optional[int] = None,
        track_name: Optional[str] = None,
    ) -> None:
        """Record a new session in state."""
        timestamp = datetime.now(timezone.utc)

        # Add to global audit history using sequential integer keys
        entry = {
            "persona_id": persona_id,
            "session_id": session_id,
            "pr_number": pr_number,
            "created_at": timestamp,
            "track": track_name
        }
        
        # Find the next sequential index
        if not self.history:
            next_idx = 0
        else:
            next_idx = max(int(k) for k in self.history.keys()) + 1
        
        self.history[str(next_idx)] = entry

        # Update track specific state
        if track_name:
            track = self.get_track(track_name)
            track.persona_id = persona_id
            track.session_id = session_id
            track.pr_number = pr_number
            track.updated_at = timestamp

    def update_pr_number(self, pr_number: int, track_name: Optional[str] = None) -> None:
        """Update the PR number for the last session."""
        keys = self.sorted_history_keys
        if keys:
            self.history[keys[0]]["pr_number"] = pr_number

        if track_name and track_name in self.tracks:
            self.tracks[track_name].pr_number = pr_number


def commit_cycle_state(state_path: Path, message: str = "chore: update cycle state") -> bool:
    """Commit the cycle state file to git via GitHub API."""
    from repo.core.github import GitHubClient
    from repo.scheduler.legacy import JULES_BRANCH

    client = GitHubClient()
    if not client.token:
        print("⚠️ No GITHUB_TOKEN found, skipping remote state persistence.")
        return False

    owner = "franklinbaldo"
    repo = "egregora"
    path = ".team/cycle_state.json"

    try:
        with open(state_path) as f:
            content = f.read()

        # Update ONLY the jules branch
        branch = JULES_BRANCH
        
        # Get current file info for SHA
        file_info = client.get_file_contents(owner, repo, path, ref=branch)
        sha = file_info.get("sha") if file_info else None

        if client.create_or_update_file(
            owner=owner,
            repo=repo,
            path=path,
            content=content,
            message=message,
            branch=branch,
            sha=sha
        ):
            print(f"✅ Updated cycle state on branch \'{branch}\' via API")
            return True
        else:
            print(f"⚠️ Failed to update cycle state on branch \'{branch}\'")
            return False

    except Exception as e:
        print(f"❌ Error persisting cycle state via API: {e}")
        return False
