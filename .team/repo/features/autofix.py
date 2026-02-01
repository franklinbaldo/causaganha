"""Jules Auto-Fixer."""

import os
import subprocess
from pathlib import Path
from typing import Any

import jinja2

from repo.core.client import TeamClient
from repo.core.github import (
    fetch_failed_logs_summary,
    fetch_full_ci_logs,
    get_base_sha,
    get_pr_details_via_gh,
    get_repo_info,
)

AUTOFIX_AUTOMATION_MODE = "AUTO_CREATE_PR"

# Active session states (not completed/failed)
ACTIVE_STATES = {"IN_PROGRESS", "AWAITING_USER_FEEDBACK", "AWAITING_PLAN_APPROVAL", "RUNNING"}


def get_active_autofix_session_for_pr(client: TeamClient, pr_number: int) -> dict[str, Any] | None:
    """Check if there's already an active auto-fix session for a given PR.

    Uses the session title pattern: '🔧 Auto-Fix PR #{pr_number}:'

    Returns:
        The active session dict if found, None otherwise.
    """
    title_prefix = f"🔧 Auto-Fix PR #{pr_number}:"

    try:
        sessions_response = client.list_sessions()
        sessions = sessions_response.get("sessions", [])

        for session in sessions:
            title = session.get("title", "")
            state = session.get("state", "")

            # Match by title prefix
            if title.startswith(title_prefix):
                # Check if session is in an active state
                if state in ACTIVE_STATES:
                    session_id = session.get("name", "").split("/")[-1]
                    print(f"🔍 Found active auto-fix session for PR #{pr_number}: {session_id} (state: {state})")
                    return session

        return None
    except Exception as e:
        print(f"⚠️  Failed to check for existing sessions: {e}")
        # Don't block on this check - allow creation to proceed
        return None


def post_pr_comment(pr_number: int, comment: str, repo_path: str = ".") -> None:
    """Post a comment on a PR using gh CLI.

    Requires gh CLI to be installed and GH_TOKEN or GITHUB_TOKEN to be set.
    """
    try:
        cmd = ["gh", "pr", "comment", str(pr_number), "--body", comment]
        subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=repo_path)
        print(f"📝 Posted comment on PR #{pr_number}")
    except FileNotFoundError:
        print(f"⚠️  gh CLI not found - skipping PR comment")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Failed to post PR comment: {e.stderr if e.stderr else e}")
    except Exception as e:
        print(f"⚠️  Failed to post PR comment: {e}")
        # Don't fail the whole operation if comment posting fails


def _public_issues_block(details: dict[str, Any], logs_summary: str) -> str:
    """Generate a public-safe summary of issues for PR comments.

    Avoids leaking full CI logs into PR comments. Returns a concise, formatted block.
    """
    failed = details.get("failed_check_names") or []
    has_conflicts = bool(details.get("has_conflicts"))

    lines: list[str] = []
    if has_conflicts:
        lines.append("- ❌ **Tem conflitos de merge** (resolve antes de rodar CI).")
    if failed:
        lines.append("- ❌ **Checks falhando**: " + ", ".join(f"`{c}`" for c in failed))
    if logs_summary:
        # Keep comment short and avoid dumping full logs in PR
        short = logs_summary[:3000]
        suffix = "\n\n_(resumo truncado)_" if len(logs_summary) > 3000 else ""
        lines.append(
            "\n<details><summary>Resumo dos logs</summary>\n\n"
            f"```text\n{short}\n```{suffix}\n</details>"
        )
    return "\n".join(lines) if lines else "- ✅ Nenhum problema detectado."


def auto_reply_to_jules(pr_number: int) -> dict[str, Any]:
    # Use repo root as cwd for git/gh commands
    repo_root = "."
    repo_info = get_repo_info()
    repo_full = repo_info["repo_full"]

    details = get_pr_details_via_gh(pr_number, repo_path=repo_root)

    if details.get("passed_all_checks") and not details.get("has_conflicts"):
        return {"status": "success", "message": "PR is healthy."}

    # Fetch failing logs
    logs_summary = ""
    full_ci_logs = ""
    if details.get("failed_check_names"):
        logs_summary = fetch_failed_logs_summary(pr_number, cwd=repo_root)
        full_ci_logs = fetch_full_ci_logs(
            pr_number=pr_number, branch=details.get("branch", ""), repo_full=repo_full, cwd=repo_root
        )

    feedback = _render_feedback_prompt(
        pr_number=pr_number,
        details=details,
        logs_summary=logs_summary,
        full_ci_logs=full_ci_logs,
    )

    client = TeamClient()
    session_id = details.get("session_id")
    last_commit_author = details.get("last_commit_author_login")
    last_commit_by_jules = bool(details.get("last_commit_by_jules"))
    reuse_existing_session = bool(session_id and last_commit_by_jules)
    creation_reason = "No session_id found"

    autonomous_instruction = (
        "\n\n**🤖 CRITICAL - Full Autonomy Required:**\n"
        "- **NEVER ask humans for help, approval, or implementation decisions**\n"
        "- **ALWAYS make your own technical decisions** using your senior developer expertise\n"
        "- **If tests fail:** Debug, fix the issue, adjust your approach - don't ask for help\n"
        "- **You are a senior developer:** Trust your experience - ship working code confidently\n"
    )

    # Decision point: Send message to existing session OR create new session
    if not reuse_existing_session:
        if session_id and not last_commit_by_jules:
            print(
                "ℹ️ Found existing Jules session, but latest commit is not from Jules "
                f"({last_commit_author or 'unknown author'}); creating a new session "
                "instead to avoid regression.",
            )
            creation_reason = "Existing session found but latest commit is not from Jules"
        session_id = None

    if not session_id:
        # Check for existing active auto-fix session for this PR (by title pattern)
        existing_session = get_active_autofix_session_for_pr(client, pr_number)
        if existing_session:
            existing_id = existing_session.get("name", "").split("/")[-1]
            existing_state = existing_session.get("state", "UNKNOWN")
            existing_title = existing_session.get("title", "")

            print(f"⏭️  Skipping creation - active auto-fix session already exists for PR #{pr_number}")
            print(f"   Session: {existing_id} | State: {existing_state} | Title: {existing_title}")

            # Post comment notifying that we're using existing session
            comment = (
                f"## 🤖 Auto-Fix: Using Existing Session\n\n"
                f"ℹ️ **An active auto-fix session already exists for this PR**\n\n"
                f"- **Session ID**: `{existing_id}`\n"
                f"- **Session State**: `{existing_state}`\n\n"
                f"Skipping creation of new session. "
                f"Track progress at: https://jules.google.com/session/{existing_id}"
            )
            post_pr_comment(pr_number, comment)

            return {
                "status": "skipped",
                "action": "existing_session_found",
                "session_id": existing_id,
                "session_state": existing_state,
                "message": f"Active auto-fix session already exists: {existing_id}",
            }

        # PR is NOT from Jules - create a new session to fix it
        print(f"📋 {creation_reason} - creating NEW Jules session for PR #{pr_number}")

        # Get repo info from environment
        owner, repo = (
            repo_full.split("/") if "/" in repo_full else ("franklinbaldo", "egregora")
        )

        # Get base branch SHA for context
        base_sha = get_base_sha(details["base_branch"], repo_path=repo_root)
        files_list = "\n".join([f"- `{f}`" for f in details["changed_files"]])

        # Construct comprehensive prompt with all PR details and errors
        new_session_prompt = (
            f"# Fix Pull Request #{pr_number}: {details['title']}\n\n"
            f"## Context\n"
            f"- **PR Number**: #{pr_number}\n"
            f"- **Current Branch**: `{details['branch']}`\n"
            f"- **Base Branch**: `{details['base_branch']}`\n"
            f"- **Base Branch Current SHA**: `{base_sha}`\n"
            f"- **Author**: {details.get('author', {}).get('login', 'Unknown')}\n\n"
            f"## Changed Files\n"
            f"{files_list}\n\n"
            f"## Original PR Description\n"
            f"{details['body'] or '_(No description provided)_'}\n\n"
            f"## Problems to Fix\n"
            f"{feedback}"
            f"{autonomous_instruction}\n\n"
            f"## Your Task\n\n"
            f"### Step 1: Fetch + merge (one-liner)\n"
            f"```bash\n"
            f"git fetch origin pull/{pr_number}/head:pr-{pr_number} && git merge --no-ff pr-{pr_number}\n"
            f"```\n\n"
            f"### Step 2-5: Fix, test, push\n"
            f"2. Investigate failures/conflicts\n"
            f"3. Fix all issues\n"
            f"4. Run tests to verify fixes\n"
            f"5. Push updates back to the PR branch:\n"
            f"```bash\n"
            f"git push origin HEAD:{details['branch']}\n"
            f"```\n\n"
            f"Start by fetching and merging the PR using the command above."
        )

        # Create new session
        try:
            new_session = client.create_session(
                prompt=new_session_prompt,
                owner=owner,
                repo=repo,
                branch=details["branch"],
                title=f"🔧 Auto-Fix PR #{pr_number}: {details['title'][:60]}",
                automation_mode=AUTOFIX_AUTOMATION_MODE,
                require_plan_approval=False,
            )

            new_session_id = new_session.get("name", "").split("/")[-1] if new_session.get("name") else "unknown"
            print(f"✅ Created new session: {new_session_id}")

            # Post success comment
            reuse_note = ""
            if details.get("session_id") and not last_commit_by_jules:
                reuse_note = (
                    f"- **Reason**: Latest commit authored by `{last_commit_author or 'unknown'}`; "
                    "started a fresh session to avoid regressions.\n"
                )

            # Generate public-safe summary (avoid leaking full CI logs)
            public_issues = _public_issues_block(details, logs_summary)

            comment = (
                f"## 🤖 Auto-Fix: New Session Created\n\n"
                f"✅ **Jules session created to fix this PR**\n\n"
                f"- **Session ID**: `{new_session_id}`\n"
                f"- **Branch**: `{details['branch']}`\n\n"
                f"{reuse_note}"
                f"### Issues to Fix (public summary):\n\n"
                f"{public_issues}\n\n"
                f"Jules will:\n"
                f"1. Fetch the PR using GitHub's special refs\n"
                f"2. Investigate the failures\n"
                f"3. Fix the issues\n"
                f"4. Push updates to this branch\n\n"
                f"Track progress at: https://jules.google.com/session/{new_session_id}"
            )
            post_pr_comment(pr_number, comment)

            return {
                "status": "success",
                "action": "created_new_session",
                "session_id": new_session_id,
                "branch": details["branch"],
            }
        except Exception as e:
            error_msg = f"Failed to create new session for PR #{pr_number}: {e!s}"
            print(f"❌ {error_msg}")

            comment = (
                f"## 🤖 Auto-Fix: Failed to Create Session\n\n"
                f"❌ **Error creating Jules session**\n\n"
                f"- **Error**: {e!s}\n\n"
                f"The auto-fixer tried to create a new Jules session to fix this PR, "
                f"but encountered an error. This could be due to:\n"
                f"- Jules API unavailable\n"
                f"- Authentication issues\n"
                f"- Rate limiting\n\n"
                f"Check the workflow logs for more details."
            )
            post_pr_comment(pr_number, comment)

            return {
                "status": "error",
                "error_type": "create_session_failed",
                "message": error_msg,
            }

    # Step 1: Get the session (separate error handling)
    try:
        session = client.get_session(session_id)
        session_state = session.get("state", "UNKNOWN")
        print(f"📡 Session {session_id} state: {session_state}")
    except Exception as e:
        error_msg = f"Failed to retrieve session {session_id}: {e!s}"
        comment = (
            f"## 🤖 Auto-Fix: Failed\n\n"
            f"❌ **Error retrieving Jules session**\n\n"
            f"- **Session ID**: `{session_id}`\n"
            f"- **Error**: {e!s}\n\n"
            f"The session may have been deleted or the API request failed. "
            f"Check the workflow logs for more details."
        )
        post_pr_comment(pr_number, comment)

        return {
            "status": "error",
            "error_type": "get_session_failed",
            "message": error_msg,
            "session_id": session_id,
        }

    # Step 2: Send message to session (separate error handling)
    try:
        message_text = (
            f"Hi Jules! New issues detected in PR #{pr_number}.\n\n"
            f"**Continue working on your current branch** (you should already have it checked out).\n\n"
            f"## Issues to Fix:\n\n"
            f"{feedback}"
            f"{autonomous_instruction}\n\n"
            f"Fix these issues, run tests, and push to the same branch when ready."
        )
        response = client.send_message(session_id, message_text)

        # Validate response (send_message should return a dict)
        if not isinstance(response, dict):
            print(f"⚠️  Unexpected response from send_message: {response}")

        print(f"✅ Message sent successfully to session {session_id}")

        # Post success comment to PR
        # Generate public-safe summary (avoid leaking full CI logs)
        public_issues = _public_issues_block(details, logs_summary)

        comment = (
            f"## 🤖 Auto-Fix: Message Sent\n\n"
            f"✅ **Fix request sent to Jules**\n\n"
            f"- **Session ID**: `{session_id}`\n"
            f"- **Session State**: `{session_state}`\n\n"
            f"### Issues (public summary):\n\n"
            f"{public_issues}\n\n"
            f"Jules will process this request and update the PR. "
            f"Check https://jules.google.com/session/{session_id} for progress."
        )
        post_pr_comment(pr_number, comment)

        return {
            "status": "success",
            "action": "messaged_existing_session",
            "session_id": session_id,
            "session_state": session_state,
        }
    except Exception as e:
        error_msg = f"Failed to send message to session {session_id} (state: {session_state}): {e!s}"
        comment = (
            f"## 🤖 Auto-Fix: Failed\n\n"
            f"❌ **Error sending message to Jules session**\n\n"
            f"- **Session ID**: `{session_id}`\n"
            f"- **Session State**: `{session_state}`\n"
            f"- **Error**: {e!s}\n\n"
            f"The message failed to send. This could be due to:\n"
            f"- Network/API timeout\n"
            f"- Session in invalid state\n"
            f"- API rate limiting\n\n"
            f"Check the workflow logs for more details."
        )
        post_pr_comment(pr_number, comment)

        return {
            "status": "error",
            "error_type": "send_message_failed",
            "message": error_msg,
            "session_id": session_id,
            "session_state": session_state,
        }


def _render_feedback_prompt(
    pr_number: int, details: dict[str, Any], logs_summary: str, full_ci_logs: str
) -> str:
    """Render the feedback prompt using Jinja for clarity and flexibility."""
    env = jinja2.Environment(
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=jinja2.StrictUndefined,
    )

    template_path = Path(__file__).parents[1] / "templates" / "autofix_prompt.md.j2"
    template = env.from_string(template_path.read_text())

    failed_check_names = details.get("failed_check_names") or []
    has_conflicts = bool(details.get("has_conflicts"))

    context = {
        "pr_number": pr_number,
        "has_conflicts": has_conflicts,
        "failed_check_names": failed_check_names,
        "logs_summary": logs_summary,
        "full_ci_logs": full_ci_logs,
    }

    return template.render(**context)
