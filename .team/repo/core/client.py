"""Jules API Client."""

import os
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from repo.core.exceptions import TeamClientError

# Default timeout: 60s for read operations, 10s for connect
DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)

# Retry configuration
MAX_RETRIES = 3

# HTTP status codes that should trigger a retry (server errors)
RETRYABLE_STATUS_CODES = {502, 503, 504}


class RetryableHTTPError(Exception):
    """Raised for HTTP errors that should be retried (5xx)."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)

class JulesSession(BaseModel):
    """Jules Session Model."""

    model_config = ConfigDict(extra="ignore")

    name: str  # sessions/UUID
    state: str
    createTime: str


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((
        httpx.ReadTimeout,
        httpx.ConnectTimeout,
        httpx.RemoteProtocolError,
        RetryableHTTPError,
    )),
    reraise=True,
)
def _request_with_retry(
    method: str,
    url: str,
    headers: dict[str, str],
    json: dict[str, Any] | None = None,
) -> httpx.Response:
    """Make an HTTP request with retry logic for transient failures.

    Retries on:
    - Connection timeouts
    - Read timeouts
    - Remote protocol errors
    - Server errors (502, 503, 504)

    """
    if method == "GET":
        response = httpx.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
    else:
        response = httpx.post(url, headers=headers, json=json, timeout=DEFAULT_TIMEOUT)

    # Check for retryable server errors (5xx)
    if response.status_code in RETRYABLE_STATUS_CODES:
        raise RetryableHTTPError(
            response.status_code,
            f"Server error {response.status_code}: {response.text[:200]}",
        )

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        # Non-retryable HTTP errors (4xx, other 5xx)
        msg = f"Jules API Error: {e.response.status_code} - {e.response.text}"
        raise TeamClientError(msg) from e
    except httpx.RequestError as e:
        # Request errors (that aren't retried or exhausted retries)
        msg = f"Jules Connection Error: {e}"
        raise TeamClientError(msg) from e

    return response


class TeamClient:
    """Client for Google Jules API.

    Note: Session state is read-only according to the Jules API specification.
    State transitions happen automatically as Jules processes sessions:
    - QUEUED -> PLANNING -> IN_PROGRESS -> COMPLETED
    - Use send_message() to respond to AWAITING_USER_FEEDBACK sessions
    - Use approve_plan() to respond to AWAITING_PLAN_APPROVAL sessions

    Reference: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions
    """

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

    def create_repoless_session(
        self,
        prompt: str,
        title: str | None = None,
        require_plan_approval: bool = False,
    ) -> dict[str, Any]:
        """Create a repoless Jules session (Jan 2026 API).

        Repoless sessions create ephemeral cloud dev environments with
        Node, Python, Rust, Bun, and other runtimes preloaded. These
        sessions don't require GitHub repository context and are ideal
        for tasks like:
        - Technical support/guidance (Oracle-like)
        - Research and analysis
        - Code generation without commit context
        - Generic programming tasks

        Repoless sessions can be reused to avoid hitting session limits
        (currently 100/day).

        Args:
            prompt: The task prompt for the session.
            title: Optional title for the session.
            require_plan_approval: Whether to require plan approval.

        Returns:
            Session response dict with 'name' field containing session ID.

        """
        url = f"{self.base_url}/sessions"
        data: dict[str, Any] = {
            "prompt": prompt,
            # No sourceContext = repoless ephemeral session
            "automationMode": "MANUAL",  # Repoless can't create PRs
            "requirePlanApproval": require_plan_approval,
        }

        if title:
            data["title"] = title

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
        """Send a message to an active session.

        Messages can be sent to sessions in various active states (not just
        AWAITING_USER_FEEDBACK). This is useful for providing clarification,
        additional context, or responding to agent questions.

        Args:
            session_id: The session ID or full resource name.
            message: The message to send.

        Returns:
            Empty dict on success (API returns empty body).

        """
        if session_id.startswith("sessions/"):
            session_id = session_id.split("/")[-1]

        url = f"{self.base_url}/sessions/{session_id}:sendMessage"
        data = {"prompt": message}
        response = _request_with_retry("POST", url, self._get_headers(), json=data)
        # API returns empty body on success
        return response.json() if response.text.strip() else {}

    def approve_plan(self, session_id: str) -> dict[str, Any]:
        """Approve a plan for a session in AWAITING_PLAN_APPROVAL state.

        Args:
            session_id: The session ID or full resource name.

        Returns:
            Empty dict on success (API returns empty body).

        """
        if session_id.startswith("sessions/"):
            session_id = session_id.split("/")[-1]

        url = f"{self.base_url}/sessions/{session_id}:approvePlan"
        response = _request_with_retry("POST", url, self._get_headers())
        # API returns empty body on success
        return response.json() if response.text.strip() else {}

    def get_activities(
        self,
        session_id: str,
        create_time_after: str | None = None,
    ) -> dict[str, Any]:
        """Get activities for a session.

        Args:
            session_id: The session ID or full resource name.
            create_time_after: Optional RFC 3339 timestamp to filter activities.
                Only returns activities created after this timestamp.
                Works as a range cursor for incremental polling (Jan 2026 API).

        Returns:
            Dictionary with 'activities' list.

        """
        if session_id.startswith("sessions/"):
            session_id = session_id.split("/")[-1]

        url = f"{self.base_url}/sessions/{session_id}/activities"

        # Add createTime filter parameter if provided (Jules API Jan 2026)
        if create_time_after:
            url = f"{url}?createTime={create_time_after}"

        response = _request_with_retry("GET", url, self._get_headers())
        return response.json()

    # Note: update_session() was removed because the Jules API specifies
    # that session.state is "Output only" and cannot be modified by clients.
    # State transitions happen automatically as Jules processes the session.
    # To unblock a session, use send_message() or approve_plan() instead.
