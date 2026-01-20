"""Jules Scheduler V2 - Clean, streamlined sequential execution.

This module provides the main scheduler logic for Jules persona execution.
It manages:
- Sequential persona scheduling from CSV
- PR status tracking and updates
- Oracle facilitator for inter-persona communication
- Session creation and management

Architecture:
- Small, focused functions (<50 lines each)
- Dependency injection for testability
- Result objects instead of void functions
- Clear separation of concerns
"""

import json
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import jinja2

from repo.core.client import TeamClient
from repo.core.github import get_open_prs, get_pr_by_session_id_any_state, get_repo_info
from repo.features.mail import get_message, list_inbox, mark_read, send_message
from repo.scheduler.legacy import JULES_BRANCH
from repo.scheduler.loader import PersonaLoader
from repo.scheduler.managers import BranchManager, PRManager, SessionOrchestrator
from repo.scheduler.models import SessionRequest
from repo.scheduler.schedule import (
    SCHEDULE_PATH,
    auto_extend,
    count_remaining_empty,
    get_active_oracle_session,
    get_current_sequence,
    load_schedule,
    register_oracle_session,
    save_schedule,
    update_sequence,
)

# ============================================================================
# CONSTANTS
# ============================================================================

JULES_BOT_AUTHOR = "app/google-labs-jules"
PERSONA_DIR = Path(".team/personas")
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# PR States
class PRState(str, Enum):
    """Pull request states."""

    DRAFT = "draft"
    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"


# Session States
class SessionState(str, Enum):
    """Jules session states."""

    AWAITING_FEEDBACK = "AWAITING_USER_FEEDBACK"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


# Schedule thresholds
SCHEDULE_AUTO_EXTEND_THRESHOLD = 10
SCHEDULE_AUTO_EXTEND_COUNT = 50
PR_FETCH_LIMIT = 50

# Jinja2 environment
JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
    undefined=jinja2.StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class PRInfo:
    """Pull request information."""

    number: int
    branch: str
    state: PRState
    is_draft: bool
    merged_at: str | None = None
    closed_at: str | None = None


@dataclass
class SyncInfo:
    """Sync patch information for persona PR updates."""

    patch_url: str
    pr_number: int
    head_branch: str


@dataclass
class SchedulerResult:
    """Result of scheduler operation."""

    success: bool
    message: str
    session_id: str | None = None
    error: Exception | None = None


# ============================================================================
# GITHUB API HELPERS
# ============================================================================

def fetch_jules_prs(state: str = "open") -> list[dict[str, Any]]:
    """Fetch Jules PRs from GitHub CLI.

    Args:
        state: PR state (open, merged, closed, all)

    Returns:
        List of PR dicts from gh CLI

    Raises:
        subprocess.CalledProcessError: If gh command fails

    """
    cmd = [
        "gh", "pr", "list",
        "--author", JULES_BOT_AUTHOR,
        "--state", state,
        "--json", "number,headRefName,state,isDraft,mergedAt,closedAt",
    ]

    if state != "all":
        cmd.extend(["-L", str(PR_FETCH_LIMIT)])

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def build_pr_lookup() -> dict[str, dict]:
    """Build a comprehensive PR lookup by branch name.

    Fetches open, merged, and closed PRs and creates a unified lookup.
    Later entries (merged/closed) don't overwrite earlier ones.

    Returns:
        Dict mapping branch name to PR info

    """
    pr_by_branch = {}

    # Fetch all PR states
    for state in ["open", "merged", "closed"]:
        try:
            prs = fetch_jules_prs(state)
            for pr in prs:
                branch = pr.get("headRefName", "")
                if branch and branch not in pr_by_branch:
                    pr_by_branch[branch] = pr
        except Exception:
            # Log but continue if a fetch fails
            pass

    return pr_by_branch


def extract_session_id(session_name: str) -> str:
    """Extract short session ID from full resource name.

    Args:
        session_name: Full name like "sessions/12345" or just "12345"

    Returns:
        Short session ID (last component after /)

    """
    return session_name.split("/")[-1] if "/" in session_name else session_name


def find_existing_session_id(
    client: TeamClient,
    sequence: str,
    persona_id: str,
    repo: str,
) -> str | None:
    """Find an existing session that matches the current sequence and persona.

    Args:
        client: Jules API client
        sequence: Sequence number (e.g., "003")
        persona_id: Persona identifier
        repo: Repository name

    Returns:
        Session ID if found, None otherwise

    """
    try:
        sessions = client.list_sessions().get("sessions", [])
    except Exception:
        return None

    sequence_prefix = f"{sequence} ".lower()
    persona_token = persona_id.lower()
    repo_token = repo.lower()

    for session in sessions:
        title = session.get("title", "") or ""
        title_lower = title.lower()
        if not title_lower.startswith(sequence_prefix):
            continue
        if persona_token not in title_lower or repo_token not in title_lower:
            continue

        session_name = session.get("name", "")
        if session_name:
            return extract_session_id(session_name)

    return None


def find_persona_pr(persona_id: str) -> SyncInfo | None:
    """Find existing PR for a persona and generate sync patch URL.

    Args:
        persona_id: The persona identifier

    Returns:
        SyncInfo if PR found, None otherwise

    """
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--author", JULES_BOT_AUTHOR,
             "--json", "number,headRefName,baseRefName,body"],
            capture_output=True, text=True, check=True
        )
        prs = json.loads(result.stdout)

        # Find PR by persona ID in branch or body
        for pr in prs:
            head = pr.get("headRefName", "").lower()
            body = pr.get("body", "").lower()
            if persona_id.lower() in head or persona_id.lower() in body:
                # Get repo info for URL
                repo_result = subprocess.run(
                    ["gh", "repo", "view", "--json", "owner,name"],
                    capture_output=True, text=True, check=True
                )
                repo_info = json.loads(repo_result.stdout)
                owner = repo_info["owner"]["login"]
                repo = repo_info["name"]

                head_branch = pr["headRefName"]
                patch_url = f"https://github.com/{owner}/{repo}/compare/{head_branch}...{JULES_BRANCH}.patch"

                return SyncInfo(
                    patch_url=patch_url,
                    pr_number=pr["number"],
                    head_branch=head_branch
                )
    except Exception:
        pass

    return None


# ============================================================================
# SESSION CREATION
# ============================================================================

def build_session_prompt(base_prompt: str, sync_info: SyncInfo | None) -> str:
    """Build session prompt with optional sync instructions.

    Args:
        base_prompt: The persona's base prompt
        sync_info: Optional sync information for PR updates

    Returns:
        Complete prompt with sync prefix if needed

    """
    if not sync_info:
        return base_prompt

    template = JINJA_ENV.get_template("prompts/sync_instruction.md.j2")
    sync_instruction = template.render(
        patch_url=sync_info.patch_url,
        pr_number=sync_info.pr_number,
        head_branch=sync_info.head_branch,
    )
    return sync_instruction + base_prompt


def create_persona_session(
    client: TeamClient,
    persona: Any,
    sequence: str,
    sync_info: SyncInfo | None,
    repo_info: dict[str, str],
    dry_run: bool = False,
) -> SchedulerResult:
    """Create a Jules session for a persona.

    Args:
        client: Jules API client
        persona: Persona object with id, emoji, prompt_body
        sequence: Sequence number (e.g., "003")
        sync_info: Optional sync information
        repo_info: Repository information
        dry_run: If True, don't actually create session

    Returns:
        SchedulerResult with success status and session_id

    """
    try:
        # Setup branch
        branch_mgr = BranchManager(JULES_BRANCH)
        branch_mgr.ensure_jules_branch_exists()

        # Get base commit
        result = subprocess.run(
            ["git", "rev-parse", JULES_BRANCH],
            capture_output=True, text=True, check=False
        )
        result.stdout.strip() if result.returncode == 0 else ""

        # Create session branch
        session_branch = branch_mgr.create_session_branch(
            base_branch=JULES_BRANCH,
            persona_id=persona.id
        )

        # Build prompt
        session_prompt = build_session_prompt(persona.prompt_body, sync_info)

        # Create session request
        request = SessionRequest(
            persona_id=persona.id,
            title=f"{sequence} {persona.emoji} {persona.id} {repo_info['repo']}",
            prompt=session_prompt,
            branch=session_branch,
            owner=repo_info["owner"],
            repo=repo_info["repo"],
            automation_mode="AUTO_CREATE_PR",
            require_plan_approval=False,
        )

        if dry_run:
            return SchedulerResult(
                success=True,
                message=f"[DRY RUN] Would create session for {persona.id}",
                session_id=None
            )

        # Create session
        orchestrator = SessionOrchestrator(client, dry_run=False)
        session_id = orchestrator.create_session(request)

        return SchedulerResult(
            success=True,
            message=f"Created session for {persona.id}",
            session_id=str(session_id)
        )

    except Exception as e:
        return SchedulerResult(
            success=False,
            message=f"Failed to create session: {e}",
            error=e
        )


# ============================================================================
# SEQUENTIAL SCHEDULER
# ============================================================================

def execute_sequential_tick(dry_run: bool = False, reset: bool = False) -> SchedulerResult:
    """Execute next persona in sequential order from schedule.csv.

    Args:
        dry_run: If True, don't create sessions or modify files
        reset: If True, reset current sequence (requires manual CSV edit)

    Returns:
        SchedulerResult with operation status

    """
    try:
        # Setup
        client = TeamClient()
        repo_info = get_repo_info()
        open_prs = get_open_prs(repo_info["owner"], repo_info["repo"])

        # Load schedule
        rows = load_schedule()
        if not rows:
            return SchedulerResult(
                success=False,
                message=f"No schedule found at {SCHEDULE_PATH}"
            )

        # Auto-extend if needed
        remaining = count_remaining_empty(rows)
        if remaining < SCHEDULE_AUTO_EXTEND_THRESHOLD:
            rows = auto_extend(rows, SCHEDULE_AUTO_EXTEND_COUNT)
            if not dry_run:
                save_schedule(rows)


        # Find current sequence
        current, schedule_modified = get_current_sequence(rows)

        # Save schedule if invalid personas were marked as closed
        if schedule_modified and not dry_run:
            save_schedule(rows)

        if not current:
            return SchedulerResult(
                success=True,
                message="All scheduled work complete"
            )

        seq = current["sequence"]
        persona_id = current["persona"]

        # Apply any pending votes for this sequence
        from repo.features.voting import VoteManager
        vote_mgr = VoteManager()
        voted_winner = vote_mgr.apply_votes(seq)
        if voted_winner and voted_winner != persona_id:
            # Votes changed the persona for this sequence
            persona_id = voted_winner
            # Reload schedule to get updated persona
            rows = load_schedule()
            current, _ = get_current_sequence(rows)
            if current:
                persona_id = current["persona"]

        # Handle reset
        if reset:
            rows = update_sequence(rows, seq, session_id="", pr_number="", pr_status="")
            if not dry_run:
                save_schedule(rows)

        # Load persona
        base_context = {**repo_info, "open_prs": open_prs}
        loader = PersonaLoader(PERSONA_DIR, base_context)
        personas = {p.id: p for p in loader.load_personas([])}

        if persona_id not in personas:
            rows = update_sequence(rows, seq, pr_status=PRState.CLOSED)
            if not dry_run:
                save_schedule(rows)
            return SchedulerResult(
                success=False,
                message=f"Persona '{persona_id}' not found"
            )

        persona = personas[persona_id]

        # Governance Check: Persona must be pleaded to the current Constitution
        from repo.features.governance import GovernanceManager
        gov = GovernanceManager()
        if not gov.is_persona_pleaded(persona_id):
            return SchedulerResult(
                success=False,
                message=f"Persona '{persona_id}' is not pleaded to the latest Team Constitution."
            )

        # Check for existing PR
        sync_info = find_persona_pr(persona.id)
        if sync_info:
            pass

        # Create session
        result = create_persona_session(
            client, persona, seq, sync_info, repo_info, dry_run
        )

        if result.success and result.session_id:

            # Update CSV
            rows = update_sequence(rows, seq, session_id=result.session_id)
            if not dry_run:
                save_schedule(rows)
        else:
            pass

        return result

    except Exception as e:
        return SchedulerResult(
            success=False,
            message=f"Scheduler error: {e}",
            error=e
        )


# ============================================================================
# PR STATUS TRACKER
# ============================================================================

def convert_pr_to_info(pr_dict: dict) -> PRInfo:
    """Convert gh CLI PR dict to PRInfo object.

    Args:
        pr_dict: PR dictionary from gh CLI

    Returns:
        PRInfo object

    """
    merged_at = pr_dict.get("mergedAt")
    closed_at = pr_dict.get("closedAt")
    is_draft = pr_dict.get("isDraft", False)

    # Determine state
    if merged_at:
        state = PRState.MERGED
    elif closed_at:
        state = PRState.CLOSED
    elif is_draft:
        state = PRState.DRAFT
    else:
        state = PRState.OPEN

    return PRInfo(
        number=pr_dict["number"],
        branch=pr_dict.get("headRefName", ""),
        state=state,
        is_draft=is_draft,
        merged_at=merged_at,
        closed_at=closed_at,
    )


def find_pr_for_session(
    session_id: str,
    persona: str,
    pr_by_branch: dict[str, dict],
    owner: str,
    repo: str,
) -> PRInfo | None:
    """Find PR for a session using session ID (primary) or persona (fallback).

    Args:
        session_id: Session ID to look up
        persona: Persona name (fallback)
        pr_by_branch: Lookup dict from branch to PR
        owner: GitHub owner
        repo: GitHub repo

    Returns:
        PRInfo if found, None otherwise

    """
    # PRIMARY: Look up by session ID via GitHub API
    if session_id:
        pr_data = get_pr_by_session_id_any_state(owner, repo, session_id)
        if pr_data:
            # Determine state from timestamps
            merged_at = pr_data.get("mergedAt")
            closed_at = pr_data.get("closedAt")
            
            if merged_at:
                state = PRState.MERGED
            elif closed_at:
                state = PRState.CLOSED
            else:
                state = PRState.OPEN

            return PRInfo(
                number=pr_data["number"],
                branch=pr_data["headRefName"],
                state=state,
                is_draft=False,  # API doesn't always provide this
                merged_at=merged_at,
                closed_at=closed_at,
            )

    # FALLBACK: Look up by persona in branch name (legacy)
    for branch, pr_dict in pr_by_branch.items():
        if persona.lower() in branch.lower():
            return convert_pr_to_info(pr_dict)

    return None


def update_schedule_pr_status(dry_run: bool = False) -> SchedulerResult:
    """Update schedule.csv with PR status from GitHub.

    Args:
        dry_run: If True, don't save changes

    Returns:
        SchedulerResult with update count

    """
    try:
        rows = load_schedule()
        if not rows:
            return SchedulerResult(success=True, message="No schedule found")

        # Find rows needing updates
        needs_update = [
            row for row in rows
            if row.get("session_id", "").strip()
            and row.get("pr_status", "").strip().lower() not in [PRState.MERGED, PRState.CLOSED]
        ]

        if not needs_update:
            return SchedulerResult(success=True, message="No updates needed")


        # Build PR lookup
        pr_by_branch = build_pr_lookup()
        repo_info = get_repo_info()

        # Update each row
        updated = 0
        for row in needs_update:
            seq = row["sequence"]
            persona = row["persona"]
            session_id = row.get("session_id", "").strip()

            pr_info = find_pr_for_session(
                session_id, persona, pr_by_branch,
                repo_info["owner"], repo_info["repo"]
            )

            if pr_info:
                current_pr = row.get("pr_number", "").strip()
                current_status = row.get("pr_status", "").strip().lower()

                if str(pr_info.number) != current_pr or pr_info.state != current_status:
                    if not dry_run:
                        rows = update_sequence(
                            rows, seq,
                            pr_number=str(pr_info.number),
                            pr_status=pr_info.state
                        )
                    updated += 1

        if updated > 0 and not dry_run:
            save_schedule(rows)
        elif updated == 0:
            pass

        return SchedulerResult(
            success=True,
            message=f"Updated {updated} rows"
        )

    except Exception as e:
        return SchedulerResult(
            success=False,
            message=f"PR tracker error: {e}",
            error=e
        )


# ============================================================================
# ORACLE FACILITATOR
# ============================================================================

def extract_persona_from_title(title: str, known_personas: list[str]) -> str | None:
    """Extract persona ID from session title.

    Args:
        title: Session title
        known_personas: List of known persona IDs (lowercase)

    Returns:
        Persona ID if found, None otherwise

    """
    title_lower = title.lower()
    for persona_id in known_personas:
        if persona_id in title_lower:
            return persona_id
    return None


def execute_facilitator_tick(dry_run: bool = False) -> SchedulerResult:
    """Facilitate communication between stuck sessions and Oracle.

    1. Collect questions from stuck sessions → send to Oracle mail
    2. Collect answers from Oracle mail → deliver to sessions
    3. Ensure Oracle session is running if needed

    Args:
        dry_run: If True, don't send messages or create sessions

    Returns:
        SchedulerResult with facilitator status

    """
    try:
        client = TeamClient()

        # Load personas for identification
        dummy_context = {
            "owner": "dummy", "repo": "dummy", "open_prs": [],
            "identity_branding": "", "pre_commit_instructions": "",
            "autonomy_block": "", "sprint_planning_block": "",
            "collaboration_block": "", "empty_queue_celebration": "",
            "journal_management": "", "sprint_context_text": ""
        }
        loader = PersonaLoader(PERSONA_DIR, dummy_context)
        loader.jinja_env.undefined = jinja2.Undefined
        all_personas = loader.load_personas([])
        persona_ids = [p.id.lower() for p in all_personas]

        # Get stuck sessions
        sessions = client.list_sessions().get("sessions", [])
        stuck_sessions = [
            s for s in sessions
            if s.get("state") == SessionState.AWAITING_FEEDBACK
        ]


        # Route questions to Oracle
        for session in stuck_sessions:
            session_id = extract_session_id(session.get("name", ""))
            title = session.get("title", "")
            persona_id = extract_persona_from_title(title, persona_ids)

            if not persona_id:
                continue

            try:
                activities = client.get_activities(session_id).get("activities", [])
                questions = [
                    a["message"]["text"]
                    for a in activities
                    if a.get("type") == "MESSAGE"
                    and a.get("message", {}).get("role") == "AGENT"
                ]

                if questions:
                    last_question = questions[-1]
                    subject = f"Help: {persona_id} (Session {session_id[:8]})"
                    body = f"Persona: {persona_id}\nSession: {session_id}\n\n{last_question}"

                    # Check if already sent
                    oracle_inbox = list_inbox("oracle", unread_only=True)
                    if not any(subject in m["subject"] for m in oracle_inbox):
                        if not dry_run:
                            send_message("facilitator", "oracle", subject, body)
            except Exception:
                pass

        # Deliver answers from Oracle
        for session in stuck_sessions:
            session_id = extract_session_id(session.get("name", ""))
            title = session.get("title", "")
            persona_id = extract_persona_from_title(title, persona_ids)

            if not persona_id:
                continue

            try:
                inbox = list_inbox(persona_id, unread_only=True)
                for msg in inbox:
                    if msg["from"] == "oracle":
                        content = get_message(persona_id, msg["key"])["body"]
                        if not dry_run:
                            client.send_message(session_id, content)
                            mark_read(persona_id, msg["key"])
            except Exception:
                pass

        # Ensure Oracle is running if needed
        oracle_inbox = list_inbox("oracle", unread_only=True)
        active_oracle = get_active_oracle_session()

        if oracle_inbox and not active_oracle:
            if not dry_run:
                execute_single_persona("oracle", dry_run=False)
        elif active_oracle:
            pass

        return SchedulerResult(success=True, message="Facilitator completed")

    except Exception as e:
        return SchedulerResult(
            success=False,
            message=f"Facilitator error: {e}",
            error=e
        )


# ============================================================================
# SINGLE PERSONA EXECUTION
# ============================================================================

def execute_single_persona(persona_id: str, dry_run: bool = False) -> SchedulerResult:
    """Execute a single persona by ID (ad-hoc execution).

    Args:
        persona_id: Persona identifier to run
        dry_run: If True, don't create session

    Returns:
        SchedulerResult with session creation status

    """
    try:
        client = TeamClient()
        repo_info = get_repo_info()
        open_prs = get_open_prs(repo_info["owner"], repo_info["repo"])

        # Load persona
        base_context = {**repo_info, "open_prs": open_prs}
        loader = PersonaLoader(PERSONA_DIR, base_context)
        personas = loader.load_personas([])

        target = None
        for persona in personas:
            if persona.id == persona_id or persona.path == str(persona_id):
                target = persona
                break

        if not target:
            return SchedulerResult(
                success=False,
                message=f"Persona '{persona_id}' not found"
            )


        # Check for sync
        sync_info = find_persona_pr(target.id)

        # Create session (no sequence for ad-hoc)
        result = create_persona_session(
            client, target, "", sync_info, repo_info, dry_run
        )

        if result.success and result.session_id:

            # Register Oracle sessions
            if target.id == "oracle" and not dry_run:
                register_oracle_session(result.session_id)
        else:
            pass

        return result

    except Exception as e:
        return SchedulerResult(
            success=False,
            message=f"Single persona error: {e}",
            error=e
        )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def run_scheduler(
    dry_run: bool = False,
    persona_id: str | None = None,
    reset: bool = False,
) -> SchedulerResult:
    """Main scheduler entry point.

    Args:
        dry_run: If True, don't make changes
        persona_id: If provided, run single persona (ad-hoc)
        reset: If True, reset current sequence

    Returns:
        SchedulerResult with overall status

    """
    try:
        # Initialize dependencies
        client = TeamClient()
        repo_info = get_repo_info()
        pr_mgr = PRManager(JULES_BRANCH)

        # 1. Facilitator (Oracle communication)
        execute_facilitator_tick(dry_run)

        # 2. Main execution
        if persona_id:
            # Ad-hoc single persona
            result = execute_single_persona(persona_id, dry_run)
        else:
            # Sequential schedule
            result = execute_sequential_tick(dry_run, reset)

        # 3. PR reconciliation (global)
        pr_mgr.reconcile_all_jules_prs(client, repo_info, dry_run)

        # 4. PR status updates
        update_schedule_pr_status(dry_run)

        # 5. Email polling
        from repo.features.polling import EmailPoller
        poller = EmailPoller(client)
        poller.poll_and_deliver()

        # 6. User Mail Sync (GitHub <-> local)
        from repo.features.mail_handler import run_sync
        run_sync()

        return result

    except Exception as e:
        return SchedulerResult(
            success=False,
            message=f"Scheduler error: {e}",
            error=e
        )


# ============================================================================
# LEGACY COMPATIBILITY
# ============================================================================

def execute_scheduled_tick(
    run_all: bool = False,
    prompt_id: str | None = None,
    dry_run: bool = False
) -> None:
    """Legacy compatibility wrapper.

    DEPRECATED: Use execute_single_persona() or run_scheduler() instead.
    """
    if not prompt_id:
        return

    execute_single_persona(prompt_id, dry_run)


def execute_parallel_cycle_tick(dry_run: bool = False) -> None:
    """Legacy compatibility wrapper.

    DEPRECATED: Use execute_sequential_tick() instead.
    """
    execute_sequential_tick(dry_run)


def execute_cycle_tick(dry_run: bool = False) -> None:
    """Legacy compatibility wrapper.

    DEPRECATED: Use execute_sequential_tick() instead.
    """
    execute_sequential_tick(dry_run)
