"""Jules Feedback Loop."""

import subprocess
import sys
from typing import Any

from repo.core.client import TeamClient
from repo.core.github import get_open_prs, get_pr_details_via_gh, get_repo_info, JULES_BOT_LOGINS


def should_trigger_feedback(pr_data: dict[str, Any]) -> bool:
    """Determine if a PR needs feedback."""
    # 1. Check CI Status - statusCheckRollup is a list of check results
    checks_rollup = pr_data.get("statusCheckRollup") or []

    # Check if any check has failed
    ci_failed = False
    for check in checks_rollup:
        status = check.get("conclusion") or check.get("status") or check.get("state")
        if status in ["FAILURE", "failure", "error", "timed_out", "ERROR"]:
            ci_failed = True
            break

    # 2. Check Reviews
    reviews = pr_data.get("latestReviews", [])
    changes_requested = any(r.get("state") == "CHANGES_REQUESTED" for r in reviews)

    return ci_failed or changes_requested


def should_skip_feedback(pr_data: dict[str, Any], comments: list[dict[str, Any]]) -> bool:
    """Check if we should skip feedback (loop prevention)."""
    if not comments:
        return False

    last_feedback_comment = None
    for c in reversed(comments):
        if "# Task: Fix Pull Request" in c["body"] or "<!-- # Task: Fix Pull Request -->" in c["body"]:
            last_feedback_comment = c
            break

    if not last_feedback_comment:
        return False

    commits = pr_data.get("commits", [])
    if not commits:
        return True

    last_commit = commits[-1]
    commit_date_str = last_commit.get("committedDate")
    comment_date_str = last_feedback_comment.get("createdAt")

    if commit_date_str and comment_date_str:
        # If comment is newer than commit, we already gave feedback for this state
        if comment_date_str > commit_date_str:
            return True

    return False


def construct_prompt(pr_data: dict[str, Any], ci_checks: list[dict[str, Any]]) -> str:
    """Construct the prompt for Jules."""
    pr_number = pr_data["number"]
    pr_title = pr_data["title"]
    branch = pr_data.get("headRefName") or pr_data.get("branch", "")

    # Analyze CI - check for failed checks
    failed_checks = [c for c in ci_checks if c.get("conclusion") in ["failure", "timed_out", "cancelled"]]
    ci_section = ""
    if failed_checks:
        ci_section = "## CI Failures\nThe following checks failed:\n"
        for check in failed_checks:
            check_url = check.get("details_url") or check.get("html_url") or "No URL"
            ci_section += f"- **{check.get('name', 'Unknown')}**: {check_url}\n"
    else:
        ci_section = "## CI Status\nCI checks passed (or none failed yet).\n"

    # Analyze Reviews
    pr_data.get("reviews", [])  # Full review history
    latest_reviews = pr_data.get("latestReviews", [])
    comments = pr_data.get("comments", [])

    review_section = "## Review Feedback\n"

    # Get recent reviews (last 3 from latest state?)
    for review in latest_reviews[-3:]:
        if review.get("state") in ["CHANGES_REQUESTED", "COMMENTED"]:
            author = review.get("author") or review.get("user") or {}
            login = author.get("login", "Unknown")
            body = review.get("body", "")
            review_section += f"### Review by {login} ({review['state']})\n{body}\n\n"

    # Get recent comments (last 5)
    for comment in comments[-5:]:
        author = comment.get("author") or comment.get("user") or {}
        login = author.get("login", "Unknown")
        body = comment.get("body", "")[:500]
        review_section += f"**{login}**: {body}...\n\n"

    return f"""
# Task: Fix Pull Request #{pr_number}

Your Pull Request "{pr_title}" on branch `{branch}` has received feedback that needs attention.

{ci_section}

{review_section}

## Instructions
1. Analyze the feedback above.
2. Examine the code in the current branch (`{branch}`).
3. Fix the reported issues (CI failures or review comments).
4. Commit and push your changes.
"""


def run_feedback_loop(dry_run: bool = False, author_filter: str = "app/google-labs-jules") -> None:
    """Run the feedback loop."""
    repo_info = get_repo_info()
    owner, repo = repo_info["owner"], repo_info["repo"]

    if owner == "unknown" or repo == "unknown":
        sys.exit(1)

    # Fetch PRs using GitHub API
    try:
        all_prs = get_open_prs(owner, repo)
        # Filter by author - check if author matches filter or is a Jules bot
        prs = []
        for pr in all_prs:
            pr_author = pr.get("author", {}).get("login", "")
            if author_filter in JULES_BOT_LOGINS:
                # If filtering for Jules bot, check against known logins
                if pr_author in JULES_BOT_LOGINS:
                    prs.append(pr)
            elif pr_author == author_filter or f"app/{pr_author}" == author_filter:
                prs.append(pr)
    except Exception:
        return

    if not prs:
        return

    client = None
    if not dry_run:
        try:
            client = TeamClient()
        except Exception:
            sys.exit(1)

    for pr_summary in prs:
        pr_num = pr_summary["number"]

        try:
            pr_details = get_pr_details_via_gh(pr_num)
        except Exception:
            continue

        comments = pr_details.get("comments", [])

        if should_skip_feedback(pr_data=pr_details, comments=comments):
            continue

        if should_trigger_feedback(pr_details):
            # Use statusCheckRollup from pr_details instead of calling gh CLI
            checks = pr_details.get("statusCheckRollup", [])

            prompt = construct_prompt(pr_details, checks)
            branch_name = pr_details["branch"]
            session_id = pr_details["session_id"]

            if not dry_run and client:
                try:
                    session_id_to_use = session_id

                    if session_id_to_use:
                        try:
                            client.send_message(session_id_to_use, prompt)
                        except Exception:
                            session_id_to_use = None  # Fallback to create new

                    if not session_id_to_use:
                        client.create_session(
                            prompt=prompt,
                            owner=owner,
                            repo=repo,
                            branch=branch_name,
                            title=f"Fix PR #{pr_num}: {pr_summary['title']}",
                            automation_mode="AUTO_CREATE_PR",
                            require_plan_approval=False,
                        )

                    marker_body = "🤖 Feedback sent to Jules session. \n<!-- # Task: Fix Pull Request -->"
                    subprocess.run(["gh", "pr", "comment", str(pr_num), "--body", marker_body], check=True)

                except Exception:
                    pass
        else:
            pass
