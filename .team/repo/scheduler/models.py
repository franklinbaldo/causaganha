"""Domain models for Jules scheduler.

These models represent the core concepts and state in the scheduler,
providing clear, type-safe interfaces for the scheduler logic.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PersonaConfig:
    """Immutable configuration for a persona.

    Attributes:
        id: Persona identifier (e.g., "curator", "refactor")
        emoji: Persona emoji (e.g., "🎭", "🔧")
        description: Role summary
        prompt_body: Rendered prompt text to send to Jules
        journal_entries: Recent journal entries for context
        path: Original path to prompt.md file
    """

    id: str
    emoji: str
    description: str
    prompt_body: str
    journal_entries: str
    path: str  # For debugging/logging


@dataclass
class CycleState:
    """Current state of the persona cycle.

    The cycle advances through personas sequentially, creating one
    Jules session per persona, waiting for PR merges before advancing.

    Attributes:
        last_session_id: Most recent cycle session ID (if any)
        last_persona_id: Persona from last session (if any)
        next_persona_id: Persona to run next
        next_persona_index: Index in cycle list
        should_increment_sprint: True if completing full cycle
        base_pr_number: PR number from last session (for branch naming)
    """

    last_session_id: str | None
    last_persona_id: str | None
    next_persona_id: str
    next_persona_index: int
    should_increment_sprint: bool
    base_pr_number: str


@dataclass
class SessionRequest:
    """Parameters for creating a Jules session.

    Attributes:
        persona_id: Persona identifier
        title: PR title (includes emoji)
        prompt: Full prompt body to send
        branch: Target base branch
        owner: GitHub repo owner
        repo: GitHub repo name
        automation_mode: Jules automation level (default: AUTO_CREATE_PR)
        require_plan_approval: Whether Jules should wait for plan approval
    """

    persona_id: str
    title: str
    prompt: str
    branch: str
    owner: str
    repo: str
    automation_mode: str = "AUTO_CREATE_PR"
    require_plan_approval: bool = False


@dataclass
class PRStatus:
    """Status of a GitHub pull request.

    Attributes:
        number: PR number
        title: PR title
        state: open, merged, or closed
        is_green: All CI checks passing
        is_mergeable: No conflicts
        base_branch: Target branch name
        head_branch: Source branch name
    """

    number: int
    title: str
    state: str  # "open", "merged", "closed"
    is_green: bool
    is_mergeable: bool
    base_branch: str
    head_branch: str

    @classmethod
    def from_gh_api(cls, pr_data: dict[str, Any]) -> "PRStatus":
        """Create PRStatus from GitHub API response."""
        return cls(
            number=pr_data.get("number", 0),
            title=pr_data.get("title", ""),
            state=pr_data.get("state", "unknown").lower(),
            is_green=cls._check_ci_status(pr_data),
            is_mergeable=pr_data.get("mergeable") != "CONFLICTING",
            base_branch=pr_data.get("baseRefName", ""),
            head_branch=pr_data.get("headRefName", ""),
        )

    @staticmethod
    def _check_ci_status(pr_data: dict[str, Any]) -> bool:
        """Check if all CI checks are passing."""
        status_checks = pr_data.get("statusCheckRollup", [])
        if not status_checks:
            return True  # No checks = passing

        for check in status_checks:
            status = (check.get("conclusion") or check.get("status") or "").upper()
            if status not in ["SUCCESS", "NEUTRAL", "SKIPPED", "COMPLETED"]:
                return False
        return True
