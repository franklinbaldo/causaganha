"""Jules API Client."""

import os
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from repo.core.exceptions import TeamClientError

# Default timeout: 60s for read operations, 10s for connect
DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)

# Retry configuration
MAX_RETRIES = 3

class JulesSession(BaseModel):
    """Jules Session Model."""

    model_config = ConfigDict(extra="ignore")

    name: str  # sessions/UUID
    state: str
    createTime: str


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError)),
    reraise=True
)
def _request_with_retry(
    method: str,
    url: str,
    headers: dict[str, str],
    json: dict[str, Any] | None = None,
) -> httpx.Response:
    """Make an HTTP request with retry logic for transient failures."""
    if method == "GET":
        response = httpx.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
    else:
        response = httpx.post(url, headers=headers, json=json, timeout=DEFAULT_TIMEOUT)
    
    # We might want to retry on 5xx errors too, but strictly following previous logic for now (timeouts)
    # However, raise_for_status might raise HTTPStatusError which we might want to wrap.
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        # Wrap HTTP errors in TeamClientError for clearer domains
        raise TeamClientError(f"Jules API Error: {e.response.status_code} - {e.response.text}") from e
    except httpx.RequestError as e:
         # Wrap Request errors (that aren't retried or exhausted retries)
        raise TeamClientError(f"Jules Connection Error: {e}") from e

    return response


class TeamClient:
    """Client for Google Jules API."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        """Initialize the Jules client."""
        self.api_key = api_key or os.environ.get("JULES_API_KEY")
        self.base_url = base_url or os.environ.get("JULES_BASE_URL", "https://jules.googleapis.com/v1alpha")

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if not self.api_key:
            msg = "JULES_API_KEY not set."
            raise ValueError(msg)
            
        headers["X-Goog-Api-Key"] = self.api_key
        return headers

    def create_session(
        self,
        prompt: str,
        owner: str,
        repo: str,
        branch: str = "main",
        title: str | None = None,
        require_plan_approval: bool = False,
        automation_mode: str = "AUTO_CREATE_PR",
    ) -> dict[str, Any]:
        """Create a new Jules session."""
        url = f"{self.base_url}/sessions"
        data = {
            "prompt": prompt,
            "sourceContext": {
                "source": f"sources/github/{owner}/{repo}",
                "githubRepoContext": {"startingBranch": branch},
            },
            "automationMode": automation_mode,
        }

        if title:
            data["title"] = title

        # Always send requirePlanApproval explicitly (even when false)
        data["requirePlanApproval"] = require_plan_approval

        response = _request_with_retry("POST", url, self._get_headers(), json=data)
        return response.json()

    def get_session(self, session_id: str) -> dict[str, Any]:
        """Get details of a specific session."""
        # Sanitize session_id if it's full resource name
        if session_id.startswith("sessions/"):
            session_id = session_id.split("/")[-1]

        url = f"{self.base_url}/sessions/{session_id}"
        response = _request_with_retry("GET", url, self._get_headers())
        return response.json()

    def list_sessions(self) -> dict[str, Any]:
        """List all sessions."""
        url = f"{self.base_url}/sessions"
        response = _request_with_retry("GET", url, self._get_headers())
        return response.json()

    def send_message(self, session_id: str, message: str) -> dict[str, Any]:
        """Send a message to an active session."""
        if session_id.startswith("sessions/"):
            session_id = session_id.split("/")[-1]

        url = f"{self.base_url}/sessions/{session_id}:sendMessage"
        data = {"prompt": message}
        response = _request_with_retry("POST", url, self._get_headers(), json=data)
        return response.json()

    def approve_plan(self, session_id: str) -> dict[str, Any]:
        """Approve a plan for a session."""
        if session_id.startswith("sessions/"):
            session_id = session_id.split("/")[-1]

        url = f"{self.base_url}/sessions/{session_id}:approvePlan"
        response = _request_with_retry("POST", url, self._get_headers())
        return response.json()

    def get_activities(self, session_id: str) -> dict[str, Any]:
        """Get activities for a session."""
        if session_id.startswith("sessions/"):
            session_id = session_id.split("/")[-1]

        url = f"{self.base_url}/sessions/{session_id}/activities"
        response = _request_with_retry("GET", url, self._get_headers())
        return response.json()

    def update_session(self, session_id: str, state: str) -> dict[str, Any]:
        """Update session state (e.g., to COMPLETED)."""
        if session_id.startswith("sessions/"):
            session_id = session_id.split("/")[-1]

        url = f"{self.base_url}/sessions/{session_id}"
        headers = self._get_headers()
        params = {"updateMask": "state"}
        data = {"state": state}
        response = httpx.patch(url, headers=headers, json=data, params=params, timeout=60.0)
        response.raise_for_status()
        return response.json()
