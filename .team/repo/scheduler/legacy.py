"""Jules Scheduler."""

import re
import subprocess
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import frontmatter
import jinja2

# Import from new package relative to execution or absolute
from repo.core.client import TeamClient
from repo.core.exceptions import BranchError, MergeError
from repo.core.github import (
    _extract_session_id,
    get_open_prs,
    get_pr_by_session_id_any_state,
    get_pr_details_via_gh,
    get_repo_info,
)
# Legacy placeholders - templates moved to .md.j2
IDENTITY_BRANDING = ""
JOURNAL_MANAGEMENT = ""
CELEBRATION = ""
PRE_COMMIT_INSTRUCTIONS = ""
from repo.features.sprints import SprintManager, sprint_manager


def load_schedule_registry(registry_path: Path) -> dict:
    if not registry_path.exists():
        return {}
    with open(registry_path, "rb") as f:
        data = tomllib.load(f)
    return data


def load_prompt_entries(prompts_dir: Path, cycle_list: list[str]) -> list[dict[str, Any]]:
    """Load prompt metadata for scheduler execution."""
    entries: list[dict[str, Any]] = []
    if cycle_list:
        base_dir = prompts_dir.parent
        for rel_path in cycle_list:
            p_file = (base_dir / rel_path).resolve()
            if not p_file.exists():
                print(f"Cycle prompt not found: {rel_path}", file=sys.stderr)
                continue
            try:
                post = frontmatter.load(p_file)
                pid = post.metadata.get("id")
                emoji = post.metadata.get("emoji", "")
                title = post.metadata.get("title", "")
                if not pid:
                    print(f"Cycle prompt missing id: {rel_path}", file=sys.stderr)
                    continue
                entries.append(
                    {"id": pid, "path": p_file, "rel_path": rel_path, "emoji": emoji, "title": title}
                )
            except Exception as exc:
                print(f"Failed to load cycle prompt {rel_path}: {exc}", file=sys.stderr)
        return entries

    base_dir = prompts_dir.parent
    for p_file in prompts_dir.glob("*/prompt.md"):
        try:
            post = frontmatter.load(p_file)
            pid = post.metadata.get("id")
            emoji = post.metadata.get("emoji", "")
            title = post.metadata.get("title", "")
            if pid:
                rel_path = str(p_file.relative_to(base_dir))
                entries.append(
                    {"id": pid, "path": p_file, "rel_path": rel_path, "emoji": emoji, "title": title}
                )
        except Exception:
            pass

    return entries


def load_prompt_block(block_name: str) -> str:
    """Load a shared prompt block from .team/blocks."""
    blocks_dir = Path(".team/blocks")
    block_path = blocks_dir / block_name
    if not block_path.exists():
        return ""
    try:
        return block_path.read_text().strip()
    except OSError:
        return ""


def ensure_journals_directory(persona_dir: Path) -> None:
    """Ensure the journals directory exists for a persona."""
    journals_dir = persona_dir / "journals"
    journals_dir.mkdir(parents=True, exist_ok=True)


def collect_journals(persona_dir: Path) -> str:
    """Collects all journal entries from the journals/ subdirectory."""
    journals_dir = persona_dir / "journals"
    if not journals_dir.exists():
        return ""

    # Collect all .md files, sorted by name
    journal_files = sorted(journals_dir.glob("*.md"))
    # Limit to the last 10 entries
    if len(journal_files) > 10:
        journal_files = journal_files[-10:]

    entries = []

    for jf in journal_files:
        try:
            content = jf.read_text().strip()
            # If frontmatter exists, strip it
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    content = parts[2].strip()

            if content:
                entries.append(f"\n--- Journal Entry: {jf.name} ---\n{content}\n")
        except Exception:
            pass

    return "\n".join(entries)


def parse_prompt_file(filepath: Path, context: dict) -> dict:
    post = frontmatter.load(filepath)
    config = post.metadata
    body_template = post.content

    full_context = {**context, **config}
    env = jinja2.Environment()

    full_context["autonomy_block"] = load_prompt_block("autonomy.md")
    full_context["sprint_planning_block"] = load_prompt_block("sprint_planning.md")

    full_context["identity_branding"] = env.from_string(IDENTITY_BRANDING).render(**full_context)
    full_context["journal_management"] = env.from_string(JOURNAL_MANAGEMENT).render(**full_context)
    full_context["empty_queue_celebration"] = env.from_string(CELEBRATION).render(**full_context)
    full_context["pre_commit_instructions"] = env.from_string(PRE_COMMIT_INSTRUCTIONS).render(**full_context)

    # Add sprint context to the body
    sprint_context = sprint_manager.get_sprint_context(config.get("id", "unknown"))
    body_template += sprint_context

    rendered_body = env.from_string(body_template).render(**full_context)

    title = config.get("title", "Jules Task")
    if "{{" in title:
        title = env.from_string(title).render(**full_context)
        config["title"] = title

    return {"config": config, "prompt": rendered_body.strip()}


def check_schedule(schedule_str: str) -> bool:
    """Check if schedule matches current time."""
    if not schedule_str:
        return False

    parts = schedule_str.split()
    if len(parts) != 5:
        return False

    min_s, hour_s, _dom_s, _month_s, dow_s = parts
    now = datetime.now(UTC)

    # Check Minute
    # GitHub Action runs every 15 mins. If cron says "0", it should only run at :00.
    # If cron says "*", it runs every time (e.g. every 15 mins).
    if min_s != "*":
        try:
            if int(min_s) != now.minute:
                # Allow a small buffer (e.g. 5 minutes) in case the GHA trigger is slightly late
                if not (now.minute >= int(min_s) and now.minute < int(min_s) + 5):
                    return False
        except ValueError:
            return False

    # Check Hour
    if hour_s != "*":
        if hour_s.startswith("*/"):
            try:
                step = int(hour_s[2:])
                if now.hour % step != 0:
                    return False
            except ValueError:
                return False
        else:
            try:
                if int(hour_s) != now.hour:
                    return False
            except ValueError:
                return False

    # Check Day of Week
    if dow_s != "*":
        py_dow = now.weekday()  # 0=Mon
        cron_dow = (py_dow + 1) % 7
        try:
            if int(dow_s) != cron_dow:
                return False
        except ValueError:
            return False

    return True


def get_pr_by_session_id(open_prs: list[dict[str, Any]], session_id: str) -> dict[str, Any] | None:
    """Find a PR that matches the given session ID."""
    for pr in open_prs:
        head_ref = pr.get("headRefName", "")
        body = pr.get("body", "") or ""
        extracted_id = _extract_session_id(head_ref, body)
        if extracted_id == session_id:
            return pr
    return None


JULES_BRANCH = "jules"
JULES_SCHEDULER_PREFIX = "jules"


def _is_scheduler_branch(branch_name: str) -> bool:
    return branch_name.lower().startswith(f"{JULES_SCHEDULER_PREFIX}-")


def _match_persona_from_branch(branch_name: str, cycle_entries: list[dict[str, Any]]) -> str | None:
    branch_lower = branch_name.lower()
    for entry in cycle_entries:
        pid = entry.get("id", "")
        if not pid:
            continue
        pid_lower = pid.lower()
        pattern = rf"(?:^|[-_/]){re.escape(pid_lower)}(?:$|[-_/])"
        if re.search(pattern, branch_lower):
            return pid
    return None


def get_last_cycle_session(
    client: TeamClient,
    cycle_entries: list[dict[str, Any]],
    repo_info: dict[str, Any],
    open_prs: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    """Find the most recent session that matches one of the cycle personas."""
    response = client.list_sessions()
    sessions = response.get("sessions", [])
    sessions_sorted = sorted(sessions, key=lambda s: s.get("createTime", ""), reverse=True)

    for session in sessions_sorted:
        session_name = session.get("name", "")
        session_id = session_name.split("/")[-1] if session_name else None
        if not session_id:
            continue

        pr = get_pr_by_session_id(open_prs, session_id)
        if not pr:
            pr = _get_pr_by_session_id_any_state(repo_info["owner"], repo_info["repo"], session_id)
        if not pr:
            start_branch = (
                session.get("sourceContext", {}).get("githubRepoContext", {}).get("startingBranch", "") or ""
            )
            if _is_scheduler_branch(start_branch):
                persona_id = _match_persona_from_branch(start_branch, cycle_entries)
                if persona_id:
                    return session_id, persona_id
            continue

        base_branch = pr.get("baseRefName", "") or ""
        if not _is_scheduler_branch(base_branch):
            continue
        persona_id = _match_persona_from_branch(base_branch, cycle_entries)
        if persona_id:
            return session_id, persona_id

    return None, None


def _get_pr_by_session_id_any_state(owner: str, repo: str, session_id: str) -> dict[str, Any] | None:
    """Proxy to allow monkeypatching in the compatibility scheduler."""
    scheduler_module = sys.modules.get("repo.scheduler")
    if scheduler_module:
        candidate = getattr(scheduler_module, "get_pr_by_session_id_any_state", None)
        if callable(candidate):
            return candidate(owner, repo, session_id)
    return get_pr_by_session_id_any_state(owner, repo, session_id)


def _ensure_scheduled_branch_exists() -> None:
    """Proxy to allow monkeypatching in the compatibility scheduler."""
    scheduler_module = sys.modules.get("repo.scheduler")
    if scheduler_module:
        candidate = getattr(scheduler_module, "ensure_scheduled_branch_exists", None)
        if callable(candidate) and candidate is not _ensure_scheduled_branch_exists:
            return candidate()
    return ensure_scheduled_branch_exists()


def _prepare_session_base_branch(
    base_branch: str,
    persona_id: str,
    base_pr_number: str = "",
    last_session_id: str | None = None,
) -> str:
    """Proxy to allow monkeypatching in the compatibility scheduler."""
    scheduler_module = sys.modules.get("repo.scheduler")
    if scheduler_module:
        candidate = getattr(scheduler_module, "prepare_session_base_branch", None)
        if callable(candidate) and candidate is not _prepare_session_base_branch:
            return candidate(
                base_branch,
                persona_id,
                base_pr_number=base_pr_number,
                last_session_id=last_session_id,
            )
    return prepare_session_base_branch(
        base_branch,
        persona_id,
        base_pr_number=base_pr_number,
        last_session_id=last_session_id,
    )


def prepare_session_base_branch(
    base_branch: str,
    persona_id: str,
    base_pr_number: str = "",
    last_session_id: str | None = None,
) -> str:
    """Create a short, stable base branch before starting a Jules session."""
    if (base_pr_number and last_session_id) or base_pr_number:
        base_ref = f"{JULES_SCHEDULER_PREFIX}-{persona_id}-pr{base_pr_number}"
    else:
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M")
        base_ref = f"{JULES_SCHEDULER_PREFIX}-{persona_id}-main-{stamp}"

    try:
        subprocess.run(["git", "fetch", "origin", base_branch], check=True, capture_output=True)
        result = subprocess.run(
            ["git", "rev-parse", f"origin/{base_branch}"], capture_output=True, text=True, check=True
        )
        base_sha = result.stdout.strip()
        print(f"Base branch '{base_branch}' is at SHA: {base_sha[:12]}")

        subprocess.run(
            ["git", "push", "origin", f"{base_sha}:refs/heads/{base_ref}"], check=True, capture_output=True
        )
        print(f"Prepared base branch '{base_ref}' from {base_branch}")
        return base_ref
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        print(f"Failed to prepare base branch: {stderr}", file=sys.stderr)
        print(f"Falling back to base branch: {base_branch}")
        return base_branch


def is_scheduled_drifted() -> bool:
    """Check if the 'jules' branch is drifted (unmergeable) with 'main'."""
    try:
        result = subprocess.run(
            ["git", "merge-tree", "--write-tree", "origin/" + JULES_BRANCH, "origin/main"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 1:
            print(f"Drift detected: Conflicting changes between 'origin/{JULES_BRANCH}' and 'origin/main'.")
            return True
        if result.returncode > 1:
            stderr = result.stderr.strip()
            print(
                f"Warning: git merge-tree failed with code {result.returncode}: {stderr}. Assuming NO drift to avoid accidental rotation."
            )
            return False
        return False
    except Exception as e:
        print(f"Warning: Error checking drift: {e}. Assuming NO drift.")
        return False


def rotate_drifted_scheduled_branch() -> None:
    """Rename drifted scheduled branch with sprint number."""
    current_sprint = sprint_manager.get_current_sprint()
    drift_branch = f"{JULES_BRANCH}-sprint-{current_sprint}"

    print(f"Drift detected in '{JULES_BRANCH}'. Rotating to '{drift_branch}'...")

    try:
        subprocess.run(
            ["git", "push", "origin", f"origin/{JULES_BRANCH}:refs/heads/{drift_branch}"],
            check=True,
            capture_output=True,
        )

        pr_title = f"Sprint {current_sprint} - Drifted work from {JULES_BRANCH}"
        pr_body = (
            f"This PR contains work from Sprint {current_sprint}.\n\n"
            f"**Sprint:** {current_sprint}\n"
            f"**Branch:** {drift_branch}\n\n"
            "The `jules` branch became unmergeable with `main`. "
            "Please review and merge manually if needed."
        )

        try:
            subprocess.run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--head",
                    drift_branch,
                    "--base",
                    "main",
                    "--title",
                    pr_title,
                    "--body",
                    pr_body,
                ],
                check=True,
                capture_output=True,
            )
            print(f"Created PR for sprint {current_sprint}: {drift_branch}")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            print(f"Warning: Failed to create PR for drift branch: {stderr}", file=sys.stderr)

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        print(f"Warning: Failed to rotate scheduled branch fully: {stderr}", file=sys.stderr)


def update_scheduled_from_main() -> bool:
    """Updates the scheduled branch with changes from main."""
    try:
        subprocess.run(["git", "config", "user.name", "Team Bot"], check=False)
        subprocess.run(["git", "config", "user.email", "team-bot@egregora.com"], check=False)
        subprocess.run(
            ["git", "checkout", "-B", JULES_BRANCH, f"origin/{JULES_BRANCH}"], check=True, capture_output=True
        )
        print(f"Merging origin/main into '{JULES_BRANCH}'...")
        subprocess.run(["git", "merge", "origin/main", "--no-edit"], check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", JULES_BRANCH], check=True, capture_output=True)
        print(f"Successfully updated '{JULES_BRANCH}' from main.")
        return True
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        print(f"Failed to update jules from main: {stderr}. Treating as drift...")
        rotate_drifted_scheduled_branch()
        return False


def ensure_scheduled_branch_exists() -> None:
    """Ensure the 'jules' branch exists and is not drifted."""
    try:
        subprocess.run(["git", "fetch", "origin"], check=True, capture_output=True)
        result = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", JULES_BRANCH],
            capture_output=True,
            text=True,
            check=True,
        )

        if result.stdout.strip():
            if is_scheduled_drifted():
                rotate_drifted_scheduled_branch()
            else:
                print(f"Branch '{JULES_BRANCH}' exists and is healthy. Updating from main...")
                if update_scheduled_from_main():
                    return

        print(f"Branch '{JULES_BRANCH}' needs recreation. Creating from main...")
        result = subprocess.run(
            ["git", "rev-parse", "origin/main"], capture_output=True, text=True, check=True
        )
        main_sha = result.stdout.strip()
        subprocess.run(
            ["git", "push", "--force", "origin", f"{main_sha}:refs/heads/{JULES_BRANCH}"],
            check=True,
            capture_output=True,
        )
        print(f"Created fresh '{JULES_BRANCH}' branch from main at {main_sha[:12]}")

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        raise BranchError(f"Failed to ensure scheduled branch exists: {stderr}") from e


def merge_pr_into_jules(pr_number: int) -> None:
    """Merge a PR into the scheduled branch using gh CLI."""
    try:
        subprocess.run(
            ["gh", "pr", "merge", str(pr_number), "--merge", "--delete-branch"],
            check=True,
            capture_output=True,
        )
        print(f"Successfully merged PR #{pr_number} into '{JULES_BRANCH}'.")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        raise MergeError(f"Failed to merge PR #{pr_number}: {stderr}") from e


def mark_pr_ready(pr_number: int) -> None:
    """Mark a PR as ready for review using gh CLI."""
    try:
        subprocess.run(["gh", "pr", "ready", str(pr_number)], check=True, capture_output=True)
        print(f"Successfully marked PR #{pr_number} as ready.")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        print(f"Warning: Failed to mark PR #{pr_number} as ready: {stderr}", file=sys.stderr)


def is_pr_green(pr_details: dict) -> bool:
    """Check if all CI checks on a PR are successful."""
    status_check_rollup = pr_details.get("statusCheckRollup", [])
    if not status_check_rollup:
        return True
    for check in status_check_rollup:
        status = (check.get("conclusion") or check.get("status") or "").upper()
        if status in ["SUCCESS", "NEUTRAL", "SKIPPED", "COMPLETED"]:
            continue
        return False
    return True


def run_cycle_step(
    client: TeamClient,
    repo_info: dict,
    cycle_entries: list[dict[str, Any]],
    open_prs: list[dict[str, Any]],
    dry_run: bool,
    base_context: dict,
) -> None:
    """Run a single step of the cycle scheduler."""
    cycle_ids = [entry["id"] for entry in cycle_entries]
    print(f"Running in CYCLE mode with order: {cycle_ids}")
    _ensure_scheduled_branch_exists()
    last_session_id, last_pid = get_last_cycle_session(client, cycle_entries, repo_info, open_prs)
    next_entry = cycle_entries[0]
    base_pr_number = ""

    if last_session_id and last_pid:
        print(f"Last recorded session: {last_session_id} ({last_pid})")
        pr = get_pr_by_session_id(open_prs, last_session_id)

        if pr:
            pr_number = pr["number"]
            base_pr_number = str(pr_number)
            print(f"Found PR for last session: #{pr_number} - {pr['title']}")
            pr_details = get_pr_details_via_gh(pr_number)
            if not is_pr_green(pr_details):
                print(f"PR #{pr_number} is not green. Waiting.")
                return

            if pr_details.get("is_draft"):
                print(f"PR #{pr_number} is a draft. Marking as ready...")
                if not dry_run:
                    mark_pr_ready(pr_number)

            print(f"PR #{pr_number} is green! Merging into '{JULES_BRANCH}'...")
            if not dry_run:
                merge_pr_into_jules(pr_number)

            if last_pid in cycle_ids:
                idx = cycle_ids.index(last_pid)
                next_idx = (idx + 1) % len(cycle_entries)
                next_entry = cycle_entries[next_idx]

                # If we completed a full cycle, increment sprint
                if next_idx == 0:
                    old_sprint = sprint_manager.get_current_sprint()
                    new_sprint = sprint_manager.increment_sprint()
                    print(f"Cycle completed! Sprint incremented: {old_sprint} → {new_sprint}")

            print(f"Next persona: {next_entry['id']}. Starting from '{JULES_BRANCH}'.")
        else:
            merged_pr = _get_pr_by_session_id_any_state(repo_info["owner"], repo_info["repo"], last_session_id)
            if merged_pr and merged_pr.get("mergedAt"):
                base_pr_number = str(merged_pr.get("number", ""))
                print(f"PR for session {last_session_id} already merged. Continuing.")
                if last_pid in cycle_ids:
                    idx = cycle_ids.index(last_pid)
                    next_idx = (idx + 1) % len(cycle_entries)
                    next_entry = cycle_entries[next_idx]
                    if next_idx == 0:
                        sprint_manager.increment_sprint()
                print(f"Next persona: {next_entry['id']}. Starting from '{JULES_BRANCH}'.")
            elif merged_pr and (merged_pr.get("state") or "").lower() == "closed":
                base_pr_number = str(merged_pr.get("number", ""))
                print(f"PR for session {last_session_id} was closed. Skipping.")
                if last_pid in cycle_ids:
                    idx = cycle_ids.index(last_pid)
                    next_idx = (idx + 1) % len(cycle_entries)
                    next_entry = cycle_entries[next_idx]
                    if next_idx == 0:
                        sprint_manager.increment_sprint()
                print(f"Next persona: {next_entry['id']}. Starting from '{JULES_BRANCH}'.")
            else:
                try:
                    session_details = client.get_session(last_session_id)
                    state = session_details.get("state")

                    # Handle terminal states
                    if state == "CANCELLED":
                        # CANCELLED means intentionally stopped - skip to next persona
                        print(f"Session {last_session_id} was cancelled. Advancing to next persona.")
                        if last_pid in cycle_ids:
                            idx = cycle_ids.index(last_pid)
                            next_idx = (idx + 1) % len(cycle_entries)
                            next_entry = cycle_entries[next_idx]
                            if next_idx == 0:
                                sprint_manager.increment_sprint()
                        print(f"Next persona: {next_entry['id']}. Starting from '{JULES_BRANCH}'.")
                        # Continue execution to create next session (don't return)
                    elif state in ["COMPLETED", "FAILED"]:
                        # Session completed/failed but no PR - ask Jules to finalize
                        print(
                            f"Session {last_session_id} is in state '{state}' but no PR was created."
                        )
                        print("Sending message to request PR creation...")
                        if not dry_run:
                            finalize_message = (
                                "The session is in a terminal state but no PR was created. "
                                "Please finalize the work by creating a Pull Request with the changes made, "
                                "or if there are no changes to make, finalize the session appropriately."
                            )
                            client.send_message(last_session_id, finalize_message)
                            print(f"Finalization message sent to session {last_session_id}.")
                        return  # Wait for Jules to create PR
                    elif state == "AWAITING_PLAN_APPROVAL":
                        print(
                            f"Session {last_session_id} is awaiting plan approval. Approving automatically..."
                        )
                        if not dry_run:
                            client.approve_plan(last_session_id)
                        return  # Wait for approval to take effect
                    elif state == "AWAITING_USER_FEEDBACK":
                        print(
                            f"Session {last_session_id} is awaiting user feedback (stuck). Sending nudge..."
                        )
                        if not dry_run:
                            nudge_text = "Please make the best decision possible and proceed autonomously to complete the task."
                            client.send_message(last_session_id, nudge_text)
                            print(f"Nudge sent to session {last_session_id}.")
                        return  # Wait for nudge to take effect
                    else:
                        print(f"PR for session {last_session_id} not found. Session state: {state}. Waiting.")
                        return
                except Exception as e:
                    print(f"Error checking/approving session {last_session_id}: {e}")
                    return
    else:
        print(f"No history found. Starting fresh cycle from '{JULES_BRANCH}'.")

    p_file = next_entry["path"]
    next_pid = next_entry["id"]

    try:
        persona_dir = p_file.parent
        ensure_journals_directory(persona_dir)
        journal_entries = collect_journals(persona_dir)
        raw_post = frontmatter.load(p_file)

        context = {
            **base_context,
            "journal_entries": journal_entries,
            "emoji": raw_post.metadata.get("emoji", ""),
            "id": raw_post.metadata.get("id", ""),
        }

        parsed = parse_prompt_file(p_file, context)
        config = parsed["config"]
        prompt_body = parsed["prompt"]

        session_branch = _prepare_session_base_branch(
            JULES_BRANCH,
            next_pid,
            base_pr_number,
            last_session_id=last_session_id,
        )
        print(f"Starting session for {next_pid} on branch '{session_branch}'...")

        # Generate title from persona metadata
        emoji = config.get("emoji", "")
        title = f"{emoji} {next_pid}: automated cycle task for {repo_info['repo']}"

        if not dry_run:
            result = client.create_session(
                prompt=prompt_body,
                owner=repo_info["owner"],
                repo=repo_info["repo"],
                branch=session_branch,
                title=title,
                automation_mode="AUTO_CREATE_PR",
                require_plan_approval=False,
            )
            session_id = result.get("name", "").split("/")[-1]
            print(f"Created session: {session_id}")
        else:
            print(f"[Dry Run] Would create session for {next_pid}.")

    except Exception as e:
        print(f"Error processing prompt {p_file.name}: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()


def run_scheduler(
    command: str, run_all: bool = False, dry_run: bool = False, prompt_id: str | None = None
) -> None:
    client = TeamClient()
    repo_info = get_repo_info()
    prompts_dir = Path(".team/personas")
    registry_path = Path(".team/schedules.toml")

    if not prompts_dir.exists():
        sys.exit(1)

    open_prs = get_open_prs(repo_info["owner"], repo_info["repo"])
    base_context = {**repo_info, "open_prs": open_prs}
    full_registry = load_schedule_registry(registry_path)
    schedules = full_registry.get("schedules", {})
    cycle_list = full_registry.get("cycle", [])
    prompt_entries = load_prompt_entries(prompts_dir, cycle_list)
    if cycle_list and not prompt_entries:
        print("Cycle list provided but no valid prompts were loaded.", file=sys.stderr)
        return

    is_cycle_mode = command == "tick" and not run_all and not prompt_id and bool(cycle_list)

    if is_cycle_mode:
        run_cycle_step(client, repo_info, prompt_entries, open_prs, dry_run, base_context)
        return

    for entry in prompt_entries:
        p_file = entry["path"]
        try:
            persona_dir = p_file.parent
            ensure_journals_directory(persona_dir)
            journal_entries = collect_journals(persona_dir)
            raw_post = frontmatter.load(p_file)
            context = {
                **base_context,
                "journal_entries": journal_entries,
                "emoji": raw_post.metadata.get("emoji", ""),
                "id": raw_post.metadata.get("id", ""),
            }
            parsed = parse_prompt_file(p_file, context)
            config = parsed["config"]
            prompt_body = parsed["prompt"]
            pid = config.get("id")
            if not pid or (prompt_id and prompt_id not in {pid, entry.get("rel_path")}):
                continue

            should_run = False
            schedule_str = schedules.get(pid) or config.get("schedule")
            if (
                run_all
                or (prompt_id == pid)
                or (command == "tick" and schedule_str and check_schedule(schedule_str))
            ):
                should_run = True

            if should_run:
                # Generate title from persona metadata
                emoji = config.get("emoji", "")
                title = f"{emoji} {pid}: scheduled task for {repo_info['repo']}"

                if not dry_run:
                    result = client.create_session(
                        prompt=prompt_body,
                        owner=repo_info["owner"],
                        repo=repo_info["repo"],
                        branch="main",
                        title=title,
                        automation_mode="AUTO_CREATE_PR",
                        require_plan_approval=False,
                    )
                    session_id = result.get("name", "").split("/")[-1]
                    print(f"Created session for {pid}: {session_id}")
                else:
                    print(f"[Dry Run] Would create session for {pid}")
        except Exception as e:
            print(f"Error processing prompt {p_file.name}: {e}", file=sys.stderr)
