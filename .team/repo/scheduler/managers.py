"""Manager classes for Jules scheduler operations."""

import contextlib
import logging
import re
import subprocess
from datetime import UTC, datetime
from typing import Any

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from repo.core.client import TeamClient
from repo.core.exceptions import BranchError, MergeError
from repo.core.github import (
    _extract_session_id,
    get_pr_by_session_id_any_state,
    get_pr_details_via_gh,
)
from repo.features.sprints import sprint_manager
from repo.features.reconciliation import ReconciliationTracker
from repo.scheduler.legacy import JULES_BRANCH, JULES_SCHEDULER_PREFIX
from repo.scheduler.models import CycleState, PersonaConfig, SessionRequest

logger = logging.getLogger(__name__)

# Timeout threshold for stuck sessions (in hours)
SESSION_TIMEOUT_HOURS = 0.5  # 30 minutes

# Weaver Integration Configuration
WEAVER_ENABLED = True  # When True, Overseer delegates merging to Weaver persona
WEAVER_SESSION_TIMEOUT_MINUTES = 30  # Wait this long before creating new Weaver session
WEAVER_MAX_FAILURES = 3  # After this many consecutive failures, fallback to auto-merge


class BranchManager:
    """Handles all git branch operations for the scheduler."""

    def __init__(self, jules_branch: str = JULES_BRANCH) -> None:
        """Initialize branch manager.

        Args:
            jules_branch: Name of the main Jules integration branch

        """
        self.team_branch = jules_branch

    def ensure_jules_branch_exists(self) -> None:
        """Ensure the Jules branch exists and is healthy.

        Creates the branch from main if it doesn't exist, or updates it
        from main if it exists and isn't drifted.

        Raises:
            BranchError: If branch operations fail

        """
        try:
            subprocess.run(["git", "fetch", "origin"], check=True, capture_output=True)  # noqa: S607

            # Check if branch exists
            result = subprocess.run(  # noqa: S603
                ["git", "ls-remote", "--heads", "origin", self.team_branch],
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout.strip():
                # Branch exists - check if drifted
                if self._is_drifted():
                    self._rotate_drifted_branch()
                elif self._update_from_main():
                    return

            # Create fresh branch from main
            result = subprocess.run(
                ["git", "rev-parse", "origin/main"], capture_output=True, text=True, check=True
            )
            main_sha = result.stdout.strip()
            subprocess.run(  # noqa: S603
                ["git", "push", "--force", "origin", f"{main_sha}:refs/heads/{self.team_branch}"],
                check=True,
                capture_output=True,
            )

        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            msg = f"Failed to ensure jules branch exists: {stderr}"
            raise BranchError(msg) from e

    def create_session_branch(
        self,
        base_branch: str,
        persona_id: str,
        base_pr_number: str = "",
        last_session_id: str | None = None,
        direct: bool = False,
    ) -> str:
        """Get the base branch for a Jules session (always direct).

        Args:
            base_branch: Source branch to branch from
            persona_id: Persona identifier (unused but kept for API compatibility)
            base_pr_number: Previous PR number (unused)
            last_session_id: Previous session ID (unused)
            direct: Unused but kept for API compatibility

        Returns:
            The base branch name (always returns base_branch)

        """
        # Always use direct branching per user requirement
        print(f"Using direct branch '{base_branch}' (no intermediary)")
        return base_branch

    def _is_drifted(self) -> bool:
        """Check if Jules branch has conflicts with main.

        Returns:
            True if there are conflicts, False otherwise

        """
        try:
            result = subprocess.run(  # noqa: S603
                ["git", "merge-tree", "--write-tree", f"origin/{self.team_branch}", "origin/main"],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode == 1:
                return True
            if result.returncode > 1:
                result.stderr.strip()
                return False
            return False
        except Exception:  # noqa: BLE001
            return False

    def _rotate_drifted_branch(self) -> tuple[int, int] | None:
        """Rename drifted Jules branch with sprint number and create PR.

        Returns:
            Tuple of (pr_number, sprint_number) if successful, None if failed

        """
        current_sprint = sprint_manager.get_current_sprint()
        drift_branch = f"{self.team_branch}-sprint-{current_sprint}"

        try:
            # Copy branch
            subprocess.run(  # noqa: S603
                ["git", "push", "origin", f"origin/{self.team_branch}:refs/heads/{drift_branch}"],
                check=True,
                capture_output=True,
            )

            # Create PR
            pr_title = f"Sprint {current_sprint} - Drifted work from {self.team_branch}"
            pr_body = (
                f"This PR contains work from Sprint {current_sprint}.\n\n"
                f"**Sprint:** {current_sprint}\n"
                f"**Branch:** {drift_branch}\n\n"
                f"The `{self.team_branch}` branch became unmergeable with `main`. "
                f"A reconciliation session will be created to merge these changes back."
            )

            try:
                result = subprocess.run(  # noqa: S603
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
                    text=True,
                )
                # Extract PR number from output (URL format: https://github.com/owner/repo/pull/123)
                pr_url = result.stdout.strip()
                pr_number = int(pr_url.split("/")[-1])
                return (pr_number, current_sprint)

            except subprocess.CalledProcessError as e:
                e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
                return None

        except subprocess.CalledProcessError as e:
            e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            return None

    def _update_from_main(self) -> bool:
        """Update Jules branch from main.

        Returns:
            True if successful, False if conflicts (triggers rotation)

        """
        try:
            subprocess.run(["git", "config", "user.name", "Jules Bot"], check=False)  # noqa: S607
            subprocess.run(["git", "config", "user.email", "jules-bot@google.com"], check=False)  # noqa: S607
            subprocess.run(  # noqa: S603
                ["git", "checkout", "-B", self.team_branch, f"origin/{self.team_branch}"],
                check=True,
                capture_output=True,
            )
            subprocess.run(["git", "merge", "origin/main", "--no-edit"], check=True, capture_output=True)  # noqa: S607
            subprocess.run(["git", "push", "origin", self.team_branch], check=True, capture_output=True)  # noqa: S603, S607
            return True
        except subprocess.CalledProcessError as e:
            e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            self._rotate_drifted_branch()
            return False

    def sync_with_main(self) -> tuple[int, int] | None:
        """Sync Jules branch with main after a PR merge.

        This ensures the next session is based on the latest main,
        capturing both cycle PRs and external changes to main.

        If sync fails (usually due to conflicts), treats it as drift:
        creates a backup branch (jules-sprint-N) with a PR for manual
        reconciliation, then recreates jules from main.

        Returns:
            Tuple of (pr_number, sprint_number) if drift occurred, None otherwise

        """
        try:
            subprocess.run(["git", "fetch", "origin"], check=True, capture_output=True)  # noqa: S607
            subprocess.run(["git", "config", "user.name", "Jules Bot"], check=False)  # noqa: S607
            subprocess.run(["git", "config", "user.email", "jules-bot@google.com"], check=False)  # noqa: S607
            subprocess.run(  # noqa: S603
                ["git", "checkout", "-B", self.team_branch, f"origin/{self.team_branch}"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "merge", "origin/main", "--no-edit", "--allow-unrelated-histories"],
                check=True,
                capture_output=True,
            )
            subprocess.run(  # noqa: S603
                ["git", "push", "origin", self.team_branch],
                check=True,
                capture_output=True,
            )
            return None  # No drift
        except subprocess.CalledProcessError as e:
            e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            return self._rotate_drifted_branch()  # Creates jules-sprint-N and PR automatically

    def merge_jules_into_main_direct(self, dry_run: bool = False) -> bool:  # noqa: FBT001, FBT002
        """Attempt to merge jules into main directly, or handle conflicts via backup PR.

        1. Fetches origin.
        2. Tries to merge origin/jules into main.
        3. If successful (clean merge), pushes main.
        4. If conflicting:
           - Pushes jules to a backup branch (jules-backup-{timestamp}).
           - Deletes remote jules branch.
           - Creates a PR from backup branch to main.
           - Recreates jules branch from main.

        Args:
            dry_run: If True, prints actions instead of executing them.

        Returns:
            True if operation completed successfully (either merge or backup),
            False on error.

        """
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        backup_branch = f"jules-backup-{timestamp}"

        try:
            subprocess.run(["git", "fetch", "origin"], check=True, capture_output=True)

            # Check for conflicts
            result = subprocess.run(  # noqa: S603
                ["git", "merge-tree", "--write-tree", "origin/main", f"origin/{self.team_branch}"],
                check=False,
                capture_output=True,
                text=True,
            )

            has_conflicts = result.returncode != 0

            if not has_conflicts:
                if dry_run:
                    logger.info("[Dry Run] Would merge '%s' into main.", self.team_branch)
                    return True

                subprocess.run(["git", "config", "user.name", "Jules Bot"], check=False)
                subprocess.run(["git", "config", "user.email", "jules-bot@google.com"], check=False)

                # Checkout main and merge
                subprocess.run(  # noqa: S603
                    ["git", "checkout", "-B", "main", "origin/main"], check=True, capture_output=True
                )
                subprocess.run(  # noqa: S603
                    ["git", "merge", f"origin/{self.team_branch}", "--no-edit"],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(  # noqa: S603
                    ["git", "push", "origin", "main"], check=True, capture_output=True
                )
                return True

            if dry_run:
                logger.info(
                    "[Dry Run] Conflicts detected. Would backup '%s' to '%s', delete remote, create PR, and reset from main.",
                    self.team_branch,
                    backup_branch,
                )
                return True

            # 1. Push current jules to backup branch
            subprocess.run(  # noqa: S603
                ["git", "push", "origin", f"origin/{self.team_branch}:refs/heads/{backup_branch}"],
                check=True,
                capture_output=True,
            )

            # 2. Delete remote jules branch
            subprocess.run(  # noqa: S603
                ["git", "push", "origin", "--delete", self.team_branch],
                check=True,
                capture_output=True,
            )

            # 3. Create PR from backup to main
            pr_title = f"Conflict Backup: {backup_branch}"
            pr_body = (
                f"Automatic backup of `{self.team_branch}` due to merge conflicts with `main`.\n\n"
                f"**Backup Branch:** `{backup_branch}`\n"
                f"**Reason:** Direct merge failed due to conflicts.\n"
                f"**Action Required:** Manual resolution and merge."
            )

            with contextlib.suppress(subprocess.CalledProcessError):
                subprocess.run(  # noqa: S603
                    [
                        "gh",
                        "pr",
                        "create",
                        "--head",
                        backup_branch,
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
                # Continue anyway to restore jules branch

            # 4. Recreate jules branch from main
            # Ensure we have latest main sha
            sha_result = subprocess.run(  # noqa: S603
                ["git", "rev-parse", "origin/main"],
                check=True,
                capture_output=True,
                text=True,
            )
            main_sha = sha_result.stdout.strip()

            subprocess.run(  # noqa: S603
                ["git", "push", "origin", f"{main_sha}:refs/heads/{self.team_branch}"],
                check=True,
                capture_output=True,
            )

            return True

        except subprocess.CalledProcessError:  # noqa: BLE001
            return False


class PRManager:
    """Handles GitHub PR operations."""

    def __init__(self, jules_branch: str = JULES_BRANCH) -> None:
        """Initialize PR manager.

        Args:
            jules_branch: Name of the Jules integration branch (for merges)

        """
        self.team_branch = jules_branch

    def is_draft(self, pr_details: dict) -> bool:
        """Check if a PR is a draft.

        Args:
            pr_details: PR details from GitHub API

        Returns:
            True if PR is a draft, False otherwise

        """
        # Check both field names for compatibility
        return pr_details.get("is_draft", False) or pr_details.get("isDraft", False)

    def mark_ready(self, pr_number: int) -> None:
        """Mark a draft PR as ready for review.

        Args:
            pr_number: PR number to mark as ready

        Raises:
            MergeError: If marking ready fails

        """
        try:
            subprocess.run(  # noqa: S603
                ["gh", "pr", "ready", str(pr_number)],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            msg = f"Failed to mark PR #{pr_number} as ready: {stderr}"
            raise MergeError(msg) from e

    def _pr_only_touches_jules(self, pr_number: int) -> bool:
        """Check if a PR's CONFLICTS are only in .team/ directory.
        
        If conflicts are restricted to .team/, we can force-accept the new changes.
        
        Args:
            pr_number: PR number to check
            
        Returns:
            True if all conflicting files are in .team/, False otherwise
        """
        import json
        try:
            # Get the list of files with conflicts from GitHub
            # The 'files' field shows all changed files and their status
            result = subprocess.run(
                ["gh", "pr", "view", str(pr_number), "--json", "files"],
                capture_output=True, text=True, check=True
            )
            data = json.loads(result.stdout)
            files = data.get("files", [])
            
            # If PR has any files outside .team/, conflicts could affect real code
            # So we need to be more conservative
            for f in files:
                path = f.get("path", "")
                # If any file is outside .team/, don't force-merge
                if not path.startswith(".team/"):
                    return False
            
            return len(files) > 0  # At least one file, all in .team/
        except Exception:
            return False  # If we can't check, assume it's not safe

    def is_green(self, pr_details: dict) -> bool:
        """Check if all CI checks on a PR are passing.

        Args:
            pr_details: PR details from GitHub API

        Returns:
            True if all checks pass (or no checks exist)

        """
        # 1. Check basic mergeability - handles both REST API (bool) and GraphQL (string)
        mergeable = pr_details.get("mergeable", False)
        # Only wait if GitHub is still computing mergeability (UNKNOWN/None)
        if mergeable == "UNKNOWN" or mergeable is None:
            return False
        if mergeable is False:
            return False

        # 2. Check mergeStateStatus (GraphQL via gh) OR mergeable_state (REST API)
        # GraphQL: CLEAN, BEHIND, BLOCKED, etc.
        # REST API: clean, behind, dirty, unstable, blocked, unknown
        state_status = pr_details.get("mergeStateStatus", "") or pr_details.get("mergeable_state", "")
        state_status_upper = state_status.upper() if state_status else ""
        
        # Only reject if CI is blocked (failing checks)
        # Allow DIRTY (conflicts) to try merge - we handle conflicts downstream
        if state_status_upper == "BLOCKED":
            return False
        
        # If state is CLEAN, BEHIND, or even DIRTY - let it try
        if state_status_upper in ["CLEAN", "BEHIND", "DIRTY"]:
            return True

        # 3. Check individual status checks if present
        status_checks = pr_details.get("statusCheckRollup", [])
        if not status_checks:
            # If no status checks and mergeable, assume safe
            return True

        # Check each status check
        for check in status_checks:
            conclusion = (check.get("conclusion") or "").upper()
            if conclusion == "FAILURE":
                return False
            
            # Accept SUCCESS, NEUTRAL, SKIPPED as passing
            if conclusion in ["SUCCESS", "NEUTRAL", "SKIPPED"]:
                continue

            legacy_state = (check.get("state") or "").upper()
            if legacy_state == "FAILURE":
                return False
            if legacy_state == "SUCCESS":
                continue
            if legacy_state in ["PENDING", "QUEUED", "IN_PROGRESS"]:
                return False
                
            # If not completed yet, not green
            status = (check.get("status") or "").upper()
            if status not in ["COMPLETED"]:
                return False

        return True

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception(
            lambda e: isinstance(e, MergeError)
            and "permission denied" not in str(e).lower()
            and "403" not in str(e).lower()
        ),
        reraise=True,
    )
    def merge_into_jules(self, pr_number: int) -> None:
        """Merge a PR into the Jules branch using gh CLI.

        First retargets the PR to the jules branch (in case it was created
        with a different base like main), then performs the merge.

        Args:
            pr_number: PR number to merge

        Raises:
            MergeError: If merge fails

        """
        try:
            # Retarget PR to jules branch to ensure proper merge flow
            subprocess.run(  # noqa: S603
                ["gh", "pr", "edit", str(pr_number), "--base", self.team_branch],
                check=True,
                capture_output=True,
            )

            # Try Rebase merge first (preferred for history)
            try:
                subprocess.run(  # noqa: S603
                    ["gh", "pr", "merge", str(pr_number), "--rebase", "--delete-branch"],
                    check=True,
                    capture_output=True,
                )
                return
            except subprocess.CalledProcessError:
                print(f"      ⚠️ Rebase merge failed for PR #{pr_number}, falling back to standard merge...")

            # Fallback: Standard Merge
            subprocess.run(  # noqa: S603
                ["gh", "pr", "merge", str(pr_number), "--merge", "--delete-branch"],
                check=True,
                capture_output=True,
            )

        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            msg = f"Failed to merge PR #{pr_number}: {stderr}"
            raise MergeError(msg) from e

    def ensure_integration_pr_exists(self, repo_info: dict[str, Any]) -> int | None:
        """Ensure a PR exists from repo branch to main for human review.

        Creates a PR if:
        - jules branch exists
        - jules is ahead of main (has commits to merge)
        - No open PR from repo to main exists

        Args:
            repo_info: Repository information (owner, repo)

        Returns:
            PR number if PR exists or was created, None if not needed

        """
        try:
            # Check if PR already exists: jules → main
            import json

            result = subprocess.run(  # noqa: S603
                ["gh", "pr", "list", "--head", self.team_branch, "--base", "main", "--json", "number"],
                capture_output=True,
                text=True,
                check=True,
            )
            prs = json.loads(result.stdout) if result.stdout.strip() else []

            if prs:
                return prs[0]["number"]

            # Check if jules is ahead of main
            # First check if branches share common ancestry (avoids unrelated histories false positives)
            merge_base_result = subprocess.run(  # noqa: S603
                ["git", "merge-base", "origin/main", f"origin/{self.team_branch}"],
                capture_output=True,
                text=True,
                check=False,
            )

            if merge_base_result.returncode != 0:
                # No common ancestor - unrelated histories
                # Use diff to check if branches are actually different
                diff_result = subprocess.run(  # noqa: S603
                    ["git", "diff", "--quiet", "origin/main", f"origin/{self.team_branch}"],
                    capture_output=True,
                    check=False,
                )
                if diff_result.returncode == 0:
                    return None
                # Branches differ - use commit count from diff-tree for accurate count
                diff_tree_result = subprocess.run(  # noqa: S603
                    [
                        "git",
                        "diff-tree",
                        "--no-commit-id",
                        "--name-only",
                        "-r",
                        "origin/main",
                        f"origin/{self.team_branch}",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                file_count = len([line for line in diff_tree_result.stdout.strip().split("\n") if line])
                commits_ahead = file_count  # Use file count as proxy when no merge-base
            else:
                # Normal case - count commits
                ahead_result = subprocess.run(  # noqa: S603
                    ["git", "rev-list", "--count", f"origin/main..origin/{self.team_branch}"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                commits_ahead = int(ahead_result.stdout.strip())

                if commits_ahead == 0:
                    return None

            # Create PR: jules → main using GitHub API (avoids GH Actions restrictions)

            from repo.core.github import GitHubClient

            pr_title = f"🤖 Integration: {self.team_branch} → main"
            pr_body = f"""## Automated Integration PR

This PR contains accumulated work from the Jules autonomous development cycle.

**Stats**:
- Commits: {commits_ahead}
- Source: `{self.team_branch}`
- Target: `main`

**Review Instructions**:
1. Review the accumulated changes from persona iterations
2. Verify all CI checks pass
3. Merge when ready to integrate into main branch

**Note**: This PR is automatically maintained by the Jules scheduler. New commits will be added as personas complete their work.
"""

            github_client = GitHubClient()
            pr_data = github_client.create_pull_request(
                owner=repo_info["owner"],
                repo=repo_info["repo"],
                title=pr_title,
                body=pr_body,
                head=self.team_branch,
                base="main",
            )

            if pr_data:
                pr_number = pr_data["number"]
                pr_data["html_url"]
                return pr_number
            return None

        except subprocess.CalledProcessError as e:
            e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            return None
        except Exception:  # noqa: BLE001
            return None

    def find_by_session_id(self, open_prs: list[dict[str, Any]], session_id: str) -> dict[str, Any] | None:
        """Find a PR matching the given session ID.

        Args:
            open_prs: List of open PRs from GitHub API
            session_id: Jules session ID to search for

        Returns:
            PR dict if found, None otherwise

        """
        for pr in open_prs:
            head_ref = pr.get("headRefName", "")
            body = pr.get("body", "") or ""
            extracted_id = _extract_session_id(head_ref, body)
            if extracted_id == session_id:
                return pr
        return None

    def reconcile_all_jules_prs(self, client: TeamClient, repo_info: dict[str, Any], dry_run: bool = False) -> list[dict]:
        """Overseer: Auto-merge Jules PRs (oldest first), return conflicts for Weaver.

        Args:
            client: Jules API client
            repo_info: Repository information
            dry_run: If True, only log actions
            
        Returns:
            List of PRs that failed to merge (conflicts for Weaver)
        """
        print("\n🔍 Overseer: Checking for autonomous PRs to reconcile...")
        import json
        
        conflict_prs = []
        
        try:
            # Fetch all open PRs with author, body, base, and creation time
            result = subprocess.run(
                ["gh", "pr", "list", "--json", "number,title,isDraft,mergeable,headRefName,baseRefName,body,author,createdAt"],
                capture_output=True, text=True, check=True
            )
            prs = json.loads(result.stdout)
            
            # Filter for Jules-initiated PRs targeting jules branch
            jules_prs = []
            for pr in prs:
                head = pr.get("headRefName", "")
                base = pr.get("baseRefName", "")
                
                # Skip if not targeting jules branch
                if base != self.team_branch:
                    continue
                if head == self.team_branch:
                    continue
                
                author = pr.get("author", {}).get("login", "")
                body = pr.get("body", "") or ""
                session_id = _extract_session_id(head, body)
                
                if author == "app/google-labs-jules" or head.startswith("jules-") or session_id:
                    jules_prs.append(pr)
            
            if not jules_prs:
                print("   No autonomous persona PRs found.")
                return []

            # Sort by creation date (oldest first)
            jules_prs.sort(key=lambda p: p.get("createdAt", ""))
            print(f"   Found {len(jules_prs)} candidate PRs (sorted oldest first).")

            for pr in jules_prs:
                pr_number = pr["number"]
                head = pr["headRefName"]
                is_draft = pr["isDraft"]
                
                print(f"   --- PR #{pr_number} ({head}) ---")

                # 1. Check if it's a draft and if session is complete
                if is_draft:
                    session_id = _extract_session_id(head, pr["body"])
                    if session_id:
                        try:
                            session = client.get_session(session_id)
                            if session.get("state") == "COMPLETED":
                                print(f"      ✅ Session {session_id} is COMPLETED. Marking PR as ready...")
                                if not dry_run:
                                    self.mark_ready(pr_number)
                                is_draft = False
                        except Exception as e:
                            print(f"      ⚠️ Failed to check session status: {e}")

                # 2. If not a draft, try to merge
                if not is_draft:
                    details = get_pr_details_via_gh(pr_number)
                    if self.is_green(details):
                        print(f"      ✅ PR is green! Attempting auto-merge...")
                        if not dry_run:
                            try:
                                self.merge_into_jules(pr_number)
                                print(f"      ✅ Successfully merged PR #{pr_number}")
                            except Exception as e:
                                # Merge failed - check if PR only touches .team/ files
                                only_jules_files = self._pr_only_touches_jules(pr_number)
                                
                                if only_jules_files:
                                    # Safe to force-accept new changes, but preserve history!
                                    print(f"      🔄 PR only touches .team/ files - resolving conflict favoring PR...")
                                    try:
                                        # 1. Checkout the PR branch
                                        # Use gh pr checkout to ensure we get the right branch configs
                                        subprocess.run(
                                            ["gh", "pr", "checkout", str(pr_number)],
                                            check=True, capture_output=True
                                        )
                                        
                                        # 2. Configure git user for resolution
                                        subprocess.run(["git", "config", "user.name", "Jules Overseer"], check=False)
                                        subprocess.run(["git", "config", "user.email", "overseer@repo.ai"], check=False)

                                        # 3. Merge base (jules) into PR, preferring PR changes (ours)
                                        # We are on PR branch, so 'ours' = PR content, 'theirs' = jules content
                                        # This resolves conflict by accepting what's in the PR
                                        subprocess.run(
                                            ["git", "merge", f"origin/{self.team_branch}", "-X", "ours", "--no-edit"],
                                            check=True, capture_output=True
                                        )

                                        # 4. Push the resolved branch back to origin
                                        subprocess.run(["git", "push"], check=True, capture_output=True)

                                        # 5. Now perform a standard merge (preserves history)
                                        subprocess.run(
                                            ["gh", "pr", "merge", str(pr_number), "--merge", "--delete-branch"],
                                            check=True, capture_output=True
                                        )
                                        print(f"      ✅ Resolved & Merged PR #{pr_number} (history preserved)")
                                        
                                    except Exception as e2:
                                        print(f"      ⚠️ History-preserving merge failed: {e2}")
                                        pr["merge_error"] = str(e2)
                                        conflict_prs.append(pr)
                                        # Try to cleanup/reset to avoid detached states affecting next loop?
                                        # Assuming next GH CLI/git commands will handle state or context manager clears it
                                else:
                                    # Has files outside .team/ - needs Weaver
                                    print(f"      ⚠️ Merge failed (conflict?): {e}")
                                    pr["merge_error"] = str(e)
                                    conflict_prs.append(pr)
                    else:
                        status_summary = details.get("mergeStateStatus", "UNKNOWN")
                        print(f"      ⏳ PR status: {status_summary}. Waiting for green checks...")

        except Exception as e:
            print(f"⚠️ Overseer Error: {e}")
        
        if conflict_prs:
            print(f"\n   🕸️ {len(conflict_prs)} PR(s) have conflicts - will trigger Weaver")
        
        return conflict_prs


class CycleStateManager:
    """Manages cycle state and progression logic."""

    def __init__(self, cycle_personas: list[PersonaConfig]) -> None:
        """Initialize cycle state manager.

        Args:
            cycle_personas: Ordered list of personas in the cycle

        """
        self.cycle_personas = cycle_personas
        self.cycle_ids = [p.id for p in cycle_personas]

    def find_last_cycle_session(
        self,
        client: TeamClient,
        repo_info: dict[str, Any],
        open_prs: list[dict[str, Any]],
    ) -> CycleState:
        """Find the most recent cycle session and determine next state.

        Args:
            client: Jules API client
            repo_info: Repository information
            open_prs: List of open PRs

        Returns:
            CycleState representing current cycle position

        """
        # Get all sessions sorted by creation time
        response = client.list_sessions()
        sessions = response.get("sessions", [])
        sessions_sorted = sorted(sessions, key=lambda s: s.get("createTime", ""), reverse=True)

        # Find most recent cycle session
        for session in sessions_sorted:
            session_name = session.get("name", "")
            session_id = session_name.split("/")[-1] if session_name else None
            if not session_id:
                continue

            # Try to find PR for this session
            pr = None
            for open_pr in open_prs:
                head_ref = open_pr.get("headRefName", "")
                body = open_pr.get("body", "") or ""
                extracted_id = _extract_session_id(head_ref, body)
                if extracted_id == session_id:
                    pr = open_pr
                    break

            # If not in open PRs, check all states
            if not pr:
                pr = get_pr_by_session_id_any_state(repo_info["owner"], repo_info["repo"], session_id)

            if not pr:
                continue

            # Check if this is a scheduler branch (from head, not base)
            head_branch = pr.get("headRefName", "") or ""
            if not head_branch.lower().startswith(f"{JULES_SCHEDULER_PREFIX}-"):
                continue

            # Extract persona from head branch
            persona_id = self._match_persona_from_branch(head_branch)
            if persona_id:
                # Found last cycle session!
                next_idx, should_increment = self.advance_cycle(persona_id)
                return CycleState(
                    last_session_id=session_id,
                    last_persona_id=persona_id,
                    next_persona_id=self.cycle_ids[next_idx],
                    next_persona_index=next_idx,
                    should_increment_sprint=should_increment,
                    base_pr_number=str(pr.get("number", "")),
                )

        # No history found - start fresh
        return CycleState(
            last_session_id=None,
            last_persona_id=None,
            next_persona_id=self.cycle_ids[0],
            next_persona_index=0,
            should_increment_sprint=False,
            base_pr_number="",
        )

    def advance_cycle(self, current_persona: str) -> tuple[int, bool]:
        """Calculate next persona index and sprint increment flag.

        Args:
            current_persona: ID of the persona that just completed

        Returns:
            Tuple of (next_index, should_increment_sprint)

        """
        if current_persona not in self.cycle_ids:
            return 0, False

        current_idx = self.cycle_ids.index(current_persona)
        next_idx = (current_idx + 1) % len(self.cycle_ids)
        should_increment = next_idx == 0  # Completed full cycle

        return next_idx, should_increment

    def _match_persona_from_branch(self, branch_name: str) -> str | None:
        """Extract persona ID from branch name.

        Args:
            branch_name: Git branch name

        Returns:
            Persona ID if found, None otherwise

        """
        branch_lower = branch_name.lower()
        for persona_id in self.cycle_ids:
            pid_lower = persona_id.lower()
            pattern = rf"(?:^|[-_/]){re.escape(pid_lower)}(?:$|[-_/])"
            if re.search(pattern, branch_lower):
                return persona_id
        return None


class SessionOrchestrator:
    """Coordinates Jules session creation."""

    def __init__(self, client: TeamClient, dry_run: bool = False) -> None:  # noqa: FBT001, FBT002
        """Initialize session orchestrator.

        Args:
            client: Jules API client
            dry_run: If True, don't actually create sessions

        """
        self.client = client
        self.dry_run = dry_run

    def create_session(self, request: SessionRequest) -> str:
        """Create a Jules session or reuse an existing active one.

        Args:
            request: Session creation parameters

        Returns:
            Session ID (or "[DRY RUN]" in dry run mode)

        """
        if self.dry_run:
            return "[DRY RUN]"

        # 1. Look for existing active session for this persona/title
        try:
            sessions_resp = self.client.list_sessions()
            sessions = sessions_resp.get("sessions", [])
            for session in sessions:
                state = session.get("state")
                title = session.get("title", "")
                
                # Check if this session is for the same persona and is still active
                # Titles look like: "⚡ absolutist: scheduled task"
                if request.persona_id in title and state not in ["COMPLETED", "FAILED", "CANCELLED", "DELETED"]:
                    session_id = session.get("name", "").split("/")[-1]
                    print(f"   🔄 Reusing existing active session for {request.persona_id}: {session_id} ({state})")
                    return session_id
        except Exception as e:
            print(f"   ⚠️ Warning: Failed to check for existing sessions: {e}")

        # 2. No active session found, create new one
        result = self.client.create_session(
            prompt=request.prompt,
            owner=request.owner,
            repo=request.repo,
            branch=request.branch,
            title=request.title,
            automation_mode=request.automation_mode,
            require_plan_approval=request.require_plan_approval,
        )

        return result.get("name", "").split("/")[-1]

    def handle_stuck_session(self, session_id: str, session_created_at: str | None = None) -> bool:
        """Handle a session that is stuck waiting for user input.

        Args:
            session_id: Session ID to check and potentially nudge
            session_created_at: ISO timestamp when session was created (from cycle state)

        Returns:
            bool: True if session should be skipped, False if should keep waiting

        """
        if self.dry_run:
            return False

        try:
            session_details = self.client.get_session(session_id)
            state = session_details.get("state")

            # Calculate elapsed time if we have creation timestamp
            elapsed_hours = None
            # Try to get creation time from passed parameter first
            if session_created_at:
                try:
                    created = datetime.fromisoformat(session_created_at)
                    now = datetime.now(UTC)
                    elapsed = now - created
                    elapsed_hours = elapsed.total_seconds() / 3600.0
                except (ValueError, AttributeError):
                    pass

            # If not available, try to get it from session details API response
            if elapsed_hours is None and "createTime" in session_details:
                try:
                    created = datetime.fromisoformat(session_details["createTime"])
                    now = datetime.now(UTC)
                    elapsed = now - created
                    elapsed_hours = elapsed.total_seconds() / 3600.0
                except (ValueError, AttributeError, KeyError):
                    pass

            # Check for timeout on IN_PROGRESS sessions
            if state == "IN_PROGRESS" and elapsed_hours is not None:
                return elapsed_hours > SESSION_TIMEOUT_HOURS

            # Check for timeout on COMPLETED/FAILED sessions without PR
            if state in ["COMPLETED", "FAILED"] and elapsed_hours is not None:
                return elapsed_hours > SESSION_TIMEOUT_HOURS

            if state == "AWAITING_PLAN_APPROVAL":
                self.client.approve_plan(session_id)
                return False

            if state == "AWAITING_USER_FEEDBACK":
                nudge_text = (
                    "Please make the best decision possible and proceed autonomously to complete the task."
                )
                self.client.send_message(session_id, nudge_text)
                return False

            return False

        except Exception:  # noqa: BLE001
            return False


class ReconciliationManager:
    """Manages drift reconciliation using Jules sessions."""

    def __init__(
        self,
        client: TeamClient,
        repo_info: dict[str, Any],
        jules_branch: str = JULES_BRANCH,
        dry_run: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """Initialize reconciliation manager.

        Args:
            client: Jules API client
            repo_info: Repository information (owner, repo)
            jules_branch: Name of the Jules integration branch
            dry_run: If True, don't actually create sessions

        """
        self.client = client
        self.repo_info = repo_info
        self.team_branch = jules_branch
        self.dry_run = dry_run

    def reconcile_drift(self, drift_pr_number: int, sprint_number: int) -> str | None:
        """Create a Jules session to reconcile drifted changes.

        Args:
            drift_pr_number: PR number of the drift backup (jules-sprint-N)
            sprint_number: Sprint number for naming

        Returns:
            Session ID of reconciliation session, or None if failed/dry-run

        """
        from repo.core.github import GitHubClient

        tracker = ReconciliationTracker()
        if not tracker.can_reconcile(sprint_number):
            return None

        # Get the PR diff
        gh_client = GitHubClient()
        diff = gh_client.get_pr_diff(self.repo_info["owner"], self.repo_info["repo"], drift_pr_number)

        if not diff:
            return None

        # Truncate diff if too large (Jules has prompt limits)
        max_diff_size = 50000  # characters
        if len(diff) > max_diff_size:
            diff = diff[:max_diff_size] + "\n\n[...diff truncated due to size...]"

        # Create reconciliation prompt
        prompt = f"""**Drift Reconciliation - Sprint {sprint_number}**

The `jules` branch diverged from `main` and was backed up to `jules-sprint-{sprint_number}`.

Your task is to reconcile the drifted changes with the current `main` branch.

**Backup PR**: #{drift_pr_number}
**Drift diff** (changes that need reconciliation):

```diff
{diff}
```

**Instructions**:
1. Review the diff carefully to understand what changed in the drifted branch
2. Apply these changes to the current codebase in a reconciliatory manner:
   - Resolve any conflicts with current code
   - Preserve the intent of the original changes
   - Ensure code quality and consistency
3. If changes are no longer relevant or conflict irreconcilably, document why in the PR
4. Create a Pull Request with the reconciled changes

**Important**: This is a reconciliation task. Be thoughtful about merging old changes with new code."""

        title = f"[Reconciliation] Sprint {sprint_number} drift"

        if self.dry_run:
            return "[DRY RUN]"

        # Create the session
        try:
            result = self.client.create_session(
                prompt=prompt,
                owner=self.repo_info["owner"],
                repo=self.repo_info["repo"],
                branch=self.team_branch,
                title=title,
                automation_mode="AUTO_CREATE_PR",
                require_plan_approval=False,
            )

            session_id = result.get("name", "").split("/")[-1]
            tracker.mark_reconciled(sprint_number, session_id)
            return session_id

        except Exception:  # noqa: BLE001
            return None
