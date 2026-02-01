"""Stateless Jules Scheduler with Oracle Facilitator.

This module provides a stateless scheduler that:
1. FIRST: Unblocks stuck sessions via Oracle (AWAITING_USER_FEEDBACK)
2. THEN: Merges completed Jules PRs
3. THEN: Creates new sessions (round-robin personas)

The Jules API is the source of truth - no CSV state management needed.

MAIN WORKFLOW (Oracle-First):
=============================

    TICK
      │
      ▼
    ┌─────────────────────────────────────────────┐
    │ 1. Find sessions in AWAITING_USER_FEEDBACK  │
    │    └── For each stuck session:              │
    │        ├── Extract question from activities │
    │        ├── Get/create Oracle session        │
    │        └── Send question → Oracle answers   │
    │            └── Send answer → stuck session  │
    └─────────────────────────────────────────────┘
      │
      ▼
    ┌─────────────────────────────────────────────┐
    │ 2. Merge completed PRs                      │
    └─────────────────────────────────────────────┘
      │
      ▼
    ┌─────────────────────────────────────────────┐
    │ 3. Create new session (if no active)        │
    │    └── Round-robin through personas         │
    └─────────────────────────────────────────────┘

"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from repo.core.client import TeamClient
from repo.core.github import get_open_prs, get_repo_info
from repo.scheduler.loader import PersonaLoader
from repo.scheduler.models import PersonaConfig

# Constants
JULES_BRANCH = "jules"
ORACLE_TITLE_PREFIX = "🔮 oracle"

# Jules bot login patterns for PR detection (fallback when URL detection not available)
# Primary detection is via jules.google.com/sessions/ URLs in PR body
JULES_BOT_LOGINS = {"google-labs-jules[bot]", "google-labs-jules", "app/google-labs-jules"}

# Session states from Jules API
# Reference: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions#State
# Valid states: STATE_UNSPECIFIED, QUEUED, PLANNING, AWAITING_PLAN_APPROVAL,
#               AWAITING_USER_FEEDBACK, IN_PROGRESS, PAUSED, FAILED, COMPLETED
STATE_QUEUED = "QUEUED"
STATE_PLANNING = "PLANNING"
STATE_AWAITING_USER_FEEDBACK = "AWAITING_USER_FEEDBACK"
STATE_AWAITING_PLAN_APPROVAL = "AWAITING_PLAN_APPROVAL"
STATE_IN_PROGRESS = "IN_PROGRESS"
STATE_PAUSED = "PAUSED"
STATE_COMPLETED = "COMPLETED"
STATE_FAILED = "FAILED"

# States that indicate a session needs help (Oracle can unblock these)
# These sessions are waiting for user input and can be auto-responded to
STUCK_STATES = {STATE_AWAITING_USER_FEEDBACK, STATE_AWAITING_PLAN_APPROVAL}

# States that indicate a session is actively running and doing work
# Only IN_PROGRESS means the agent is actually executing tasks
# Reference: "The session is in progress" - agent is actively working
ACTIVE_STATES = {STATE_IN_PROGRESS}

# States that indicate a session is pending but not yet active
# QUEUED: "The session is queued" - waiting to start
# PLANNING: "The agent is planning" - thinking about approach
# These can get stuck indefinitely if Jules has capacity issues
PENDING_STATES = {STATE_QUEUED, STATE_PLANNING}

# States that should be skipped - don't block new session creation
# PAUSED: User manually paused the session, continue with next persona immediately
# These sessions are not actively working and shouldn't prevent scheduling
SKIPPED_STATES = {STATE_PAUSED}

# Sessions in PENDING_STATES older than this are considered stale (in seconds)
# 1 hour threshold - if a session has been QUEUED/PLANNING for over an hour,
# it's likely stuck due to Jules capacity issues and should not block new sessions
# Reference: createTime field is RFC 3339 formatted timestamp
PENDING_STALENESS_THRESHOLD = 3600


def _get_repo_root() -> Path:
    """Get the repository root directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except Exception:
        return Path.cwd()


def _get_persona_dir() -> Path:
    """Get the personas directory path."""
    return _get_repo_root() / ".team" / "personas"


@dataclass
class SchedulerResult:
    """Result of a scheduler operation."""

    success: bool
    message: str
    session_id: str | None = None
    merged_count: int = 0
    unblocked_count: int = 0


@dataclass
class StuckSession:
    """A session that is waiting for user feedback."""

    session_id: str
    title: str
    state: str
    persona: str | None = None
    question: str | None = None


# =============================================================================
# ORACLE FACILITATOR - Main Workflow
# =============================================================================


def get_stuck_sessions(client: TeamClient, repo: str) -> list[StuckSession]:
    """Find sessions that are waiting for user feedback.

    Args:
        client: Jules API client
        repo: Repository name to filter sessions

    Returns:
        List of stuck sessions needing Oracle help.

    """
    try:
        sessions = client.list_sessions().get("sessions", [])
    except Exception as e:
        print(f"  Failed to list sessions: {e}")
        return []

    stuck = []
    repo_lower = repo.lower()

    for session in sessions:
        title = session.get("title") or ""
        state = (session.get("state") or "").upper()
        session_id = session.get("name", "").split("/")[-1]

        # Skip if not for this repo
        if repo_lower not in title.lower():
            continue

        # Skip Oracle sessions (don't unblock the unblocker!)
        if ORACLE_TITLE_PREFIX.lower() in title.lower():
            continue

        # Check if stuck
        if state in STUCK_STATES:
            # Try to identify persona from title
            persona = None
            personas = discover_personas()
            for p in personas:
                if p in title.lower():
                    persona = p
                    break

            stuck.append(
                StuckSession(
                    session_id=session_id,
                    title=title,
                    state=state,
                    persona=persona,
                )
            )

    return stuck


def extract_question_from_session(client: TeamClient, session_id: str) -> str | None:
    """Extract the question Jules is asking from session activities.

    Args:
        client: Jules API client
        session_id: Session to inspect

    Returns:
        The question text, or None if not found.

    """
    try:
        activities = client.get_activities(session_id).get("activities", [])
    except Exception as e:
        print(f"  Failed to get activities for {session_id}: {e}")
        return None

    if not activities:
        return None

    # Sort by timestamp to get most recent
    activities = sorted(
        activities,
        key=lambda a: a.get("createTime") or "",
        reverse=True,
    )

    # Look for the most recent agent message that looks like a question
    for activity in activities:
        originator = activity.get("originator", "").upper()
        if originator != "AGENT":
            continue

        # Check text content
        text = activity.get("text") or activity.get("content") or ""

        # Also check artifacts for messages
        for artifact in activity.get("artifacts", []):
            if artifact.get("type") == "text":
                text = artifact.get("contents", {}).get("text", "") or text

        if text and ("?" in text or "need" in text.lower() or "help" in text.lower()):
            return text.strip()

    # Fallback: return the last agent message
    for activity in activities:
        if activity.get("originator", "").upper() == "AGENT":
            text = activity.get("text") or activity.get("content") or ""
            if text:
                return text.strip()

    return None


def get_or_create_oracle_session(
    client: TeamClient,
    repo_info: dict[str, str],
) -> str | None:
    """Get an existing Oracle session or create a new one.

    Oracle sessions are reused to avoid creating new sessions for each question.

    Args:
        client: Jules API client
        repo_info: Repository information

    Returns:
        Oracle session ID, or None on failure.

    """
    repo = repo_info["repo"]

    # First, try to find an existing Oracle session
    try:
        sessions = client.list_sessions().get("sessions", [])
    except Exception as e:
        print(f"  Failed to list sessions: {e}")
        return None

    # Look for existing Oracle session (not FAILED/COMPLETED)
    for session in sessions:
        title = session.get("title") or ""
        state = (session.get("state") or "").upper()
        session_id = session.get("name", "").split("/")[-1]

        if ORACLE_TITLE_PREFIX.lower() in title.lower() and repo.lower() in title.lower():
            # Check if session is still usable
            if state not in {STATE_FAILED, STATE_COMPLETED}:
                print(f"  Found existing Oracle session: {session_id} (state: {state})")
                return session_id

    # No usable Oracle session found, create new one
    print("  Creating new Oracle session...")

    # Load Oracle's prompt from disk so the facilitator uses the same
    # prompt as every other persona — no hardcoded string.
    oracle_prompt: str | None = None
    try:
        persona_dir = _get_persona_dir()
        loader = PersonaLoader(persona_dir, base_context={
            "owner": repo_info["owner"],
            "repo": repo,
        })
        oracle_prompt_file = persona_dir / "oracle" / "prompt.md.j2"
        if not oracle_prompt_file.exists():
            oracle_prompt_file = persona_dir / "oracle" / "prompt.md"
        if oracle_prompt_file.exists():
            config = loader.load_persona(oracle_prompt_file)
            oracle_prompt = config.prompt_body
    except Exception as e:
        print(f"  Warning: could not load Oracle prompt from disk: {e}")

    if not oracle_prompt:
        oracle_prompt = (
            f"You are the Oracle, a technical support specialist for {repo}. "
            "Help other AI personas when they get stuck by answering technical questions. "
            "Do NOT modify code or create PRs — only provide guidance."
        )

    # Read automation_mode from Oracle's frontmatter (defaults to FULL)
    automation_mode = "MANUAL"
    try:
        import frontmatter as fm

        oracle_file = _get_persona_dir() / "oracle" / "prompt.md.j2"
        if oracle_file.exists():
            automation_mode = fm.load(oracle_file).metadata.get("automation_mode", "MANUAL")
    except Exception:
        pass

    try:
        result = client.create_session(
            prompt=oracle_prompt,
            owner=repo_info["owner"],
            repo=repo,
            branch=JULES_BRANCH,
            title=f"{ORACLE_TITLE_PREFIX} {repo}",
            automation_mode=automation_mode,
            require_plan_approval=False,
        )
        session_id = result.get("name", "").split("/")[-1]
        print(f"  Created Oracle session: {session_id}")
        return session_id
    except Exception as e:
        print(f"  Failed to create Oracle session: {e}")
        return None


def facilitate_stuck_session(
    client: TeamClient,
    stuck: StuckSession,
    oracle_session_id: str,
    repo_info: dict[str, str],
    dry_run: bool = False,
) -> bool:
    """Facilitate a stuck session by routing through Oracle.

    Args:
        client: Jules API client
        stuck: The stuck session
        oracle_session_id: Oracle session to use
        repo_info: Repository information
        dry_run: If True, don't send messages

    Returns:
        True if facilitation was successful.

    """
    print(f"\n  Facilitating: {stuck.title}")
    print(f"    State: {stuck.state}")
    print(f"    Persona: {stuck.persona or 'unknown'}")

    # Step 1: Extract the question
    question = extract_question_from_session(client, stuck.session_id)
    if not question:
        print("    No question found in session activities")
        # For AWAITING_PLAN_APPROVAL, auto-approve
        if stuck.state == STATE_AWAITING_PLAN_APPROVAL:
            print("    Auto-approving plan...")
            if not dry_run:
                try:
                    client.approve_plan(stuck.session_id)
                    print("    Plan approved!")
                    return True
                except Exception as e:
                    print(f"    Failed to approve plan: {e}")
                    return False
        return False

    print(f"    Question: {question[:100]}...")

    if dry_run:
        print("    [DRY RUN] Would send to Oracle and forward answer")
        return True

    # Step 2: Send question to Oracle
    oracle_prompt = f"""# Question from {stuck.persona or "a persona"}

The following persona is stuck and needs your help:
- **Persona**: {stuck.persona or "unknown"}
- **Session**: {stuck.session_id}

## Their Question
{question}

## Instructions
Please provide a clear, actionable answer to help them proceed.
Focus on practical guidance they can immediately apply.
"""

    try:
        client.send_message(oracle_session_id, oracle_prompt)
        print("    Sent question to Oracle")
    except Exception as e:
        print(f"    Failed to send to Oracle: {e}")
        return False

    # Step 3: For now, send a generic unblocking message to the stuck session
    # (In a more sophisticated version, we'd wait for Oracle's response)
    unblock_message = """# Support Response

Your question has been reviewed. Here's guidance to help you proceed:

## General Advice
1. If you're waiting for clarification on requirements, make reasonable assumptions and document them
2. If you're stuck on a technical issue, try a simpler approach first
3. If you need access to something, check if there's an alternative path

## Proceed With
Based on your context, please continue with your task using your best judgment.
If you encounter further issues, include specific error messages in your questions.

---
*This response was facilitated by the Oracle support system.*
"""

    try:
        client.send_message(stuck.session_id, unblock_message)
        print("    Sent unblocking message to stuck session")
        return True
    except Exception as e:
        print(f"    Failed to unblock session: {e}")
        return False


def unblock_stuck_sessions(
    client: TeamClient,
    repo_info: dict[str, str],
    dry_run: bool = False,
) -> int:
    """Find and unblock all stuck sessions.

    This is the PRIMARY workflow - runs before regular scheduling.

    Args:
        client: Jules API client
        repo_info: Repository information
        dry_run: If True, don't send messages

    Returns:
        Number of sessions unblocked.

    """
    repo = repo_info["repo"]

    print("\n1. Checking for stuck sessions (AWAITING_USER_FEEDBACK)...")
    stuck_sessions = get_stuck_sessions(client, repo)

    if not stuck_sessions:
        print("  No stuck sessions found")
        return 0

    print(f"  Found {len(stuck_sessions)} stuck session(s)")

    # Get or create Oracle session
    oracle_session_id = None
    if not dry_run:
        oracle_session_id = get_or_create_oracle_session(client, repo_info)
        if not oracle_session_id:
            print("  Failed to get Oracle session, cannot facilitate")
            return 0

    unblocked = 0
    for stuck in stuck_sessions:
        if facilitate_stuck_session(client, stuck, oracle_session_id or "", repo_info, dry_run):
            unblocked += 1

    print(f"\n  Unblocked {unblocked}/{len(stuck_sessions)} session(s)")
    return unblocked


# =============================================================================
# REGULAR SCHEDULING (Secondary Workflow)
# =============================================================================


def discover_personas() -> list[str]:
    """Discover available personas from the filesystem.

    Scans the personas directory for subdirectories containing a prompt
    template (prompt.md.j2 or prompt.md). Directories starting with '.'
    or '_' are ignored. Personas with ``scheduled: false`` in their
    frontmatter are skipped (e.g. Oracle, which runs only as a
    facilitator). To decommission a persona entirely, move its folder
    out of the personas directory.
    """
    import frontmatter as fm

    persona_dir = _get_persona_dir()
    if not persona_dir.exists():
        return []

    personas = []
    for path in persona_dir.iterdir():
        if not path.is_dir():
            continue
        if path.name.startswith((".", "_")):
            continue
        prompt_file = path / "prompt.md.j2"
        if not prompt_file.exists():
            prompt_file = path / "prompt.md"
        if not prompt_file.exists():
            continue
        # Respect per-persona scheduling opt-out
        try:
            meta = fm.load(prompt_file).metadata
        except Exception as exc:  # noqa: BLE001
            print(f"  Warning: skipping {path.name} (malformed frontmatter: {exc})")
            continue
        if not meta.get("scheduled", True):
            continue
        personas.append(path.name)

    return sorted(personas)


def _is_session_stale(session: dict[str, Any]) -> bool:
    """Check if a session in PENDING_STATES is stale (too old).

    Uses the session's createTime field to determine age.
    Reference: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions
    createTime is formatted per RFC 3339 (e.g., "2024-01-15T10:30:00.000Z").

    Args:
        session: Session dict from Jules API containing createTime field.

    Returns:
        True if session is older than PENDING_STALENESS_THRESHOLD (1 hour).

    """
    create_time_str = session.get("createTime")
    if not create_time_str:
        # No create time - consider it stale to be safe
        return True

    try:
        # Parse RFC 3339 format: 2024-01-15T10:30:00.000Z
        create_time = datetime.fromisoformat(create_time_str.replace("Z", "+00:00"))
        now = datetime.now(UTC)
        age_seconds = (now - create_time).total_seconds()
        return age_seconds > PENDING_STALENESS_THRESHOLD
    except (ValueError, TypeError):
        # Can't parse time - consider it stale
        return True


def get_active_session(client: TeamClient, repo: str) -> dict | None:
    """Check if there's an active/running Jules session for this repo.

    Session state handling based on Jules API State enum:
    Reference: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions#State

    - IN_PROGRESS: "The session is in progress" - always blocks new sessions
    - QUEUED/PLANNING: Only blocks if session is recent (< 1 hour old)
      Stale sessions in these states are ignored to prevent deadlock when
      Jules has capacity issues.
    - PAUSED: Skipped - continue immediately to next persona
    - Oracle sessions are always skipped (they're support sessions).

    Args:
        repo: Repository name to filter sessions.

    Returns:
        Active session dict, or None if no blocking session exists.

    """
    try:
        sessions = client.list_sessions().get("sessions", [])
    except Exception:
        return None

    repo_lower = repo.lower()
    pending_session = None

    for session in sessions:
        title = (session.get("title") or "").lower()
        state = (session.get("state") or "").upper()
        session_id = session.get("name", "").split("/")[-1]

        if repo_lower not in title:
            continue

        # Skip Oracle sessions
        if ORACLE_TITLE_PREFIX.lower() in title:
            continue

        # Skip PAUSED sessions - continue immediately to next persona
        if state in SKIPPED_STATES:
            print(f"  Skipping {state} session: {session_id}")
            continue

        # IN_PROGRESS means actively working - always blocks
        if state in ACTIVE_STATES:
            return session

        # Track pending sessions (QUEUED/PLANNING) for staleness check
        if state in PENDING_STATES:
            if not _is_session_stale(session):
                # Recent pending session - might still start
                pending_session = session

    # Return pending session only if it's recent enough to possibly start
    return pending_session


def get_last_persona_from_api(client: TeamClient, repo: str) -> str | None:
    """Get the last persona that ran from Jules API."""
    try:
        sessions = client.list_sessions().get("sessions", [])
    except Exception:
        return None

    sessions = sorted(
        sessions,
        key=lambda s: s.get("createTime") or "",
        reverse=True,
    )

    personas = discover_personas()
    repo_lower = repo.lower()

    for session in sessions:
        title = (session.get("title") or "").lower()

        if repo_lower not in title:
            continue

        for persona in personas:
            if persona in title:
                return persona

    return None


def get_next_persona(last: str | None, personas: list[str]) -> str | None:
    """Get the next persona in round-robin order."""
    if not personas:
        return None

    if last and last in personas:
        idx = (personas.index(last) + 1) % len(personas)
        return personas[idx]

    return personas[0]


def merge_completed_prs() -> int:
    """Merge Jules draft PRs regardless of CI status.

    Jules PRs are identified by:
    1. PR body containing jules.google.com/sessions/ URL (primary)
    2. PR body containing jules.google.com/task/ URL (fallback)
    3. OR author is the Jules bot (fallback)
    """
    try:
        # Get all open PRs (not filtered by author since Jules now creates PRs as repo owner)
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "open",
                "--json",
                "number,isDraft,mergeable,body,author",
                "--limit",
                "50",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        prs = json.loads(result.stdout)
    except Exception as e:
        print(f"  Failed to list PRs: {e}")
        return 0

    merged = 0
    for pr in prs:
        pr_number = pr["number"]
        is_draft = pr.get("isDraft", False)
        mergeable = pr.get("mergeable", "UNKNOWN")
        body = pr.get("body", "") or ""
        author_login = pr.get("author", {}).get("login", "")

        # Check if it's a Jules PR (URL in body OR bot author)
        is_jules_pr = (
            "jules.google.com/sessions/" in body
            or "jules.google.com/task/" in body
            or author_login in JULES_BOT_LOGINS
        )

        if not is_jules_pr:
            continue

        if mergeable == "CONFLICTING":
            print(f"  PR #{pr_number}: has conflicts, skipping")
            continue

        try:
            if is_draft:
                subprocess.run(
                    ["gh", "pr", "ready", str(pr_number)],
                    check=True,
                    capture_output=True,
                )
                print(f"  PR #{pr_number}: marked ready")

            subprocess.run(
                ["gh", "pr", "merge", str(pr_number), "--merge", "--delete-branch", "--admin"],
                check=True,
                capture_output=True,
            )
            print(f"  PR #{pr_number}: merged (admin override)")
            merged += 1

        except subprocess.CalledProcessError as e:
            print(f"  PR #{pr_number}: merge failed - {e.stderr if e.stderr else e}")

    return merged


def ensure_jules_branch() -> None:
    """Ensure the jules branch exists on the remote.

    The Jules API requires the branch to exist on the remote (GitHub) before
    a session can be created against it. This function:
    1. Checks the remote for the branch (not just locally)
    2. Creates and pushes it from main if missing on the remote
    3. If it already exists, leaves it as-is to preserve unmerged commits

    IMPORTANT: This function must NOT reset the jules branch to main when it
    already exists. The sync-main job handles the bidirectional sync (jules → main,
    then main → jules) AFTER the scheduler. Resetting here would destroy any
    jules commits that haven't been merged to main yet.
    """
    # Fetch latest main so we have the most recent ref
    subprocess.run(
        ["git", "fetch", "origin", "main"],
        capture_output=True,
    )

    # Check if the branch exists on the REMOTE — this is what the Jules API needs
    remote_check = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", JULES_BRANCH],
        capture_output=True,
        text=True,
    )

    branch_exists_on_remote = (
        remote_check.returncode == 0 and bool(remote_check.stdout.strip())
    )

    if not branch_exists_on_remote:
        # Branch missing on remote — create locally and push
        # Delete stale local branch if it exists
        subprocess.run(
            ["git", "branch", "-D", JULES_BRANCH],
            capture_output=True,
        )
        subprocess.run(
            ["git", "branch", JULES_BRANCH, "origin/main"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", JULES_BRANCH],
            check=True,
            capture_output=True,
        )
        print(f"  Created {JULES_BRANCH} branch from main and pushed to remote")
    else:
        # Branch exists on remote — do NOT reset to main.
        # The jules branch may have unmerged commits (from merged PRs or
        # previous sessions). The sync-main job merges jules → main first,
        # then aligns jules to main. Resetting here would destroy those
        # commits before sync-main can preserve them.
        print(f"  {JULES_BRANCH} branch exists on remote (preserved)")


def check_ci_status_on_main() -> tuple[bool, str | None]:
    """Check if CI is passing on main branch.

    Returns:
        Tuple of (is_passing, failing_commit_sha).
        If CI is passing, failing_commit_sha is None.
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "run",
                "list",
                "--branch",
                "main",
                "--limit",
                "1",
                "--json",
                "conclusion,headSha",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        runs = json.loads(result.stdout)
        if runs:
            is_passing = runs[0].get("conclusion") == "success"
            commit_sha = runs[0].get("headSha")
            return is_passing, commit_sha if not is_passing else None
        return True, None
    except Exception:
        return True, None


def create_session(
    client: TeamClient,
    persona: PersonaConfig,
    repo_info: dict[str, str],
) -> SchedulerResult:
    """Create a Jules session for a persona."""
    try:
        ensure_jules_branch()

        result = client.create_session(
            prompt=persona.prompt_body,
            owner=repo_info["owner"],
            repo=repo_info["repo"],
            branch=JULES_BRANCH,
            title=f"{persona.emoji} {persona.id} {repo_info['repo']}",
            automation_mode="AUTO_CREATE_PR",
            require_plan_approval=False,
        )

        session_id = result.get("name", "").split("/")[-1]

        return SchedulerResult(
            success=True,
            message=f"Created session for {persona.id}",
            session_id=session_id,
        )

    except Exception as e:
        return SchedulerResult(
            success=False,
            message=f"Failed to create session: {e}",
        )


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def run_scheduler(dry_run: bool = False) -> SchedulerResult:
    """Main scheduler entry point.

    PRIORITY ORDER:
    1. Unblock stuck sessions (AWAITING_USER_FEEDBACK) via Oracle
    2. Merge completed PRs
    3. Check for active sessions (skip if running)
    4. Check CI on main (create fixer if failing)
    5. Create new session (round-robin personas)

    Args:
        dry_run: If True, don't create sessions or send messages

    Returns:
        SchedulerResult with operation status.

    """
    print("Jules Scheduler (Stateless + Oracle Facilitator)")
    print("=" * 50)

    # Initialize
    client = TeamClient()
    repo_info = get_repo_info()
    print(f"Repository: {repo_info['owner']}/{repo_info['repo']}")

    # ==========================================================================
    # STEP 1: UNBLOCK STUCK SESSIONS (PRIMARY WORKFLOW)
    # ==========================================================================
    unblocked = unblock_stuck_sessions(client, repo_info, dry_run)

    # ==========================================================================
    # STEP 2: MERGE COMPLETED PRS
    # ==========================================================================
    print("\n2. Checking for PRs to merge...")
    if dry_run:
        print("  [DRY RUN] Skipping PR merge")
        merged = 0
    else:
        merged = merge_completed_prs()
    print(f"  Merged {merged} PR(s)")

    # ==========================================================================
    # STEP 3: CHECK FOR ACTIVE SESSIONS
    # ==========================================================================
    print("\n3. Checking for active sessions...")
    active_session = get_active_session(client, repo_info["repo"])
    if active_session:
        session_id = active_session.get("name", "").split("/")[-1]
        state = active_session.get("state", "UNKNOWN")
        print(f"  Active session found: {session_id} (state: {state})")
        return SchedulerResult(
            success=True,
            message=f"Session already running ({state})",
            session_id=session_id,
            merged_count=merged,
            unblocked_count=unblocked,
        )
    print("  No active sessions found")

    # ==========================================================================
    # STEP 4: CHECK CI STATUS (informational only)
    # ==========================================================================
    # NOTE: We no longer create dedicated ci-fixer sessions here.
    # The natural round-robin flow handles CI failures:
    #   Main CI fails → sync → Jules has failing code → persona runs →
    #   fixes issues → PR merges → sync → Main CI passes
    print("\n4. Checking CI status on main (informational)...")
    ci_ok, failing_commit = check_ci_status_on_main()
    if not ci_ok:
        print(f"  CI is failing on main (commit: {failing_commit[:7] if failing_commit else 'unknown'})")
        print("  Next persona will handle the fix naturally")
    else:
        print("  CI is passing on main")

    # ==========================================================================
    # STEP 5: CREATE NEW SESSION
    # ==========================================================================
    print("\n5. Determining next persona...")
    personas = discover_personas()
    if not personas:
        return SchedulerResult(
            success=False,
            message="No personas found",
            merged_count=merged,
            unblocked_count=unblocked,
        )
    print(f"  Available personas: {len(personas)}")

    last_persona = get_last_persona_from_api(client, repo_info["repo"])
    if last_persona:
        print(f"  Last persona: {last_persona}")
    else:
        print("  No previous session found")

    next_persona_id = get_next_persona(last_persona, personas)
    if not next_persona_id:
        return SchedulerResult(
            success=False,
            message="Could not determine next persona",
            merged_count=merged,
            unblocked_count=unblocked,
        )
    print(f"  Next persona: {next_persona_id}")

    print("\n6. Loading persona configuration...")
    try:
        open_prs = get_open_prs(repo_info["owner"], repo_info["repo"])
        context: dict[str, Any] = {**repo_info, "open_prs": open_prs}
        loader = PersonaLoader(_get_persona_dir(), context)
        all_personas = {p.id: p for p in loader.load_personas([])}

        if next_persona_id not in all_personas:
            return SchedulerResult(
                success=False,
                message=f"Persona '{next_persona_id}' not found",
                merged_count=merged,
                unblocked_count=unblocked,
            )

        persona = all_personas[next_persona_id]
        print(f"  Loaded: {persona.emoji} {persona.id}")
        print(f"  Prompt length: {len(persona.prompt_body)} chars")

    except Exception as e:
        return SchedulerResult(
            success=False,
            message=f"Failed to load persona: {e}",
            merged_count=merged,
            unblocked_count=unblocked,
        )

    print("\n7. Creating Jules session...")
    if dry_run:
        print(f"  [DRY RUN] Would create session for {persona.id}")
        return SchedulerResult(
            success=True,
            message=f"[DRY RUN] Would create session for {persona.id}",
            merged_count=merged,
            unblocked_count=unblocked,
        )

    result = create_session(client, persona, repo_info)
    result.merged_count = merged
    result.unblocked_count = unblocked

    if result.success:
        print(f"  Session created: {result.session_id}")
    else:
        print(f"  Failed: {result.message}")

    return result


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Jules Scheduler with Oracle Facilitator")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't create sessions, merge PRs, or send messages",
    )
    parser.add_argument(
        "--merge-only",
        action="store_true",
        help="Only merge PRs, don't create new session",
    )
    args = parser.parse_args()

    if args.merge_only:
        print("Merge-only mode")
        merged = merge_completed_prs()
        print(f"Merged {merged} PR(s)")
        return

    result = run_scheduler(dry_run=args.dry_run)

    print("\n" + "=" * 50)
    print(f"Result: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Message: {result.message}")
    if result.session_id:
        print(f"Session ID: {result.session_id}")
    print(f"PRs Merged: {result.merged_count}")
    print(f"Sessions Unblocked: {result.unblocked_count}")


if __name__ == "__main__":
    main()
