"GitHub utilities for Jules."

import io
import json
import os
import re
import zipfile
from typing import Any
from urllib.parse import urlparse

import httpx
from repo.core.exceptions import GitHubError

JULES_BOT_LOGINS = {"google-labs-jules[bot]", "app/google-labs-jules", "google-labs-jules"}


class GitHubClient:
    """GitHub API Client using httpx."""

    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Jules-Bot",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Make a GET request to GitHub API."""
        if not self.token:
            return None

        url = f"{self.base_url}/{endpoint}"
        try:
            response = httpx.get(url, headers=self.headers, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return None

    def _get_raw(self, endpoint: str) -> httpx.Response | None:
        """Make a GET request returning raw response (for logs/zips)."""
        if not self.token:
            return None

        url = f"{self.base_url}/{endpoint}"
        try:
            response = httpx.get(url, headers=self.headers, follow_redirects=True, timeout=60.0)
            response.raise_for_status()
            return response
        except httpx.HTTPError:
            return None

    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str | None:
        """Get the diff/patch for a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            Unified diff as string, or None if unavailable
        """
        if not self.token:
            return None

        # Use GitHub's .diff endpoint to get unified diff
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = self.headers.copy()
        headers["Accept"] = "application/vnd.github.v3.diff"

        try:
            response = httpx.get(url, headers=headers, timeout=60.0)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError:
            return None
    def get_file_contents(self, owner: str, repo: str, path: str, ref: str = "main") -> dict[str, Any] | None:
        """Get file contents and its SHA."""
        return self._get(f"repos/{owner}/{repo}/contents/{path}", params={"ref": ref})

    def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = "main",
        sha: str | None = None,
    ) -> bool:
        """Create or update a file in the repository via API."""
        import base64

        if not self.token:
            return False

        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        data = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
        }
        if sha:
            data["sha"] = sha

        try:
            response = httpx.put(url, headers=self.headers, json=data, timeout=30.0)
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            print(f"⚠️ GitHub API File Update Error: {e}")
            return False

    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> dict[str, Any] | None:
        """Create a pull request using GitHub API.

        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            body: PR description
            head: Branch containing changes
            base: Target branch (default: main)

        Returns:
            PR data dict with number, url, etc. or None on failure
        """
        if not self.token:
            return None

        url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
        data = {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
        }

        try:
            response = httpx.post(url, headers=self.headers, json=data, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"⚠️ GitHub API Create PR Error: {e}")
            return None

    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Create a GitHub issue."""
        if not self.token:
            return None

        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        data = {
            "title": title,
            "body": body,
        }
        if labels:
            data["labels"] = labels

        try:
            response = httpx.post(url, headers=self.headers, json=data, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"⚠️ GitHub API Create Issue Error: {e}")
            return None

    def list_issue_comments(self, owner: str, repo: str, issue_number: int) -> list[dict[str, Any]]:
        """List comments for a GitHub issue."""
        if not self.token:
            return []

        url = f"repos/{owner}/{repo}/issues/{issue_number}/comments"
        return self._get(url) or []

    def create_issue_comment(self, owner: str, repo: str, issue_number: int, body: str) -> dict[str, Any] | None:
        """Post a comment on a GitHub issue."""
        if not self.token:
            return None

        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        data = {"body": body}

        try:
            response = httpx.post(url, headers=self.headers, json=data, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"⚠️ GitHub API Create Comment Error: {e}")
            return None

def get_open_prs(owner: str, repo: str) -> list[dict[str, Any]]:
    """Fetch open PRs using GitHub API."""
    client = GitHubClient()
    if not client.token:
        return []

    try:
        prs = client._get(
            f"repos/{owner}/{repo}/pulls",
            params={"state": "open", "per_page": 100, "sort": "updated", "direction": "desc"},
        )
    except Exception:
        return []

    if not prs:
        return []

    mapped_prs = []
    for pr in prs:
        mapped_prs.append({
            "number": pr["number"],
            "title": pr["title"],
            "headRefName": pr["head"]["ref"],
            "baseRefName": pr["base"]["ref"],
            "url": pr["html_url"],
            "author": {"login": pr["user"]["login"]},
            "isDraft": pr["draft"],
            "body": pr["body"] or "",
        })
    return mapped_prs


def get_pr_by_session_id_any_state(owner: str, repo: str, session_id: str) -> dict[str, Any] | None:
    """Fetch a PR by session ID across all PR states."""
    client = GitHubClient()
    if not client.token:
        return None

    try:
        prs = client._get(
            f"repos/{owner}/{repo}/pulls",
            params={"state": "all", "per_page": 100, "sort": "updated", "direction": "desc"},
        )
    except Exception:
        return None

    for pr in prs or []:
        head_ref = pr["head"]["ref"]
        body = pr["body"] or ""
        extracted_id = _extract_session_id(head_ref, body)
        if extracted_id == session_id:
            return {
                "number": pr["number"],
                "title": pr["title"],
                "headRefName": head_ref,
                "baseRefName": pr["base"]["ref"],
                "mergedAt": pr["merged_at"],
                "closedAt": pr["closed_at"],
                "state": pr["state"].upper(),
            }

    return None


def get_pr_details_via_gh(pr_number: int, repo_path: str = ".") -> dict[str, Any]:
    """Retrieve PR details using GitHub API."""
    repo_info = get_repo_info()
    owner = repo_info["owner"]
    repo = repo_info["repo"]
    
    client = GitHubClient()
    if not client.token:
        raise GitHubError("No GitHub token provided")

    try:
        # 1. Get PR details
        pr = client._get(f"repos/{owner}/{repo}/pulls/{pr_number}")
        if not pr:
            raise GitHubError(f"PR {pr_number} not found")

        # 2. Get Commits (last 100)
        commits_data = client._get(f"repos/{owner}/{repo}/pulls/{pr_number}/commits", params={"per_page": 100}) or []
        
        # 3. Get Reviews
        reviews_data = client._get(f"repos/{owner}/{repo}/pulls/{pr_number}/reviews") or []
        
        # 4. Get Comments (Issue comments)
        comments_data = client._get(f"repos/{owner}/{repo}/issues/{pr_number}/comments") or []

        # 5. Get Checks (Latest commit SHA)
        head_sha = pr["head"]["sha"]
        check_runs = client._get(f"repos/{owner}/{repo}/commits/{head_sha}/check-runs")
        checks_rollup = check_runs.get("check_runs", []) if check_runs else []

    except Exception as e:
        raise GitHubError(f"Failed to fetch details for PR {pr_number}: {e}") from e

    branch = pr["head"]["ref"]
    body = pr["body"] or ""
    session_id = _extract_session_id(branch, body)
    
    mapped_commits = []
    for c in commits_data:
        mapped_commits.append({
            "sha": c["sha"],
            "message": c["commit"]["message"],
            "author": {"login": c["author"]["login"] if c["author"] else c["commit"]["author"]["name"]},
            "authors": [{"login": c["author"]["login"] if c["author"] else c["commit"]["author"]["name"]}] # compat
        })

    last_commit_author = _get_last_commit_author_login(mapped_commits)
    all_passed, failed_check_names = _analyze_checks(checks_rollup)

    return {
        "number": pr_number,
        "title": pr["title"],
        "body": body,
        "session_id": session_id,
        "branch": branch,
        "base_branch": pr["base"]["ref"],
        "is_draft": pr["draft"],
        "has_conflicts": pr.get("mergeable_state") == "dirty", # Approximate mapping
        "passed_all_checks": all_passed,
        "failed_check_names": failed_check_names,
        "mergeable": pr.get("mergeable"),
        "mergeable_state": pr.get("mergeable_state"),
        "mergeStateStatus": (pr.get("mergeable_state") or "UNKNOWN").upper(),
        "changed_files": [], # Would need another API call, skipping for perf unless critical
        "reviews": reviews_data,
        "latestReviews": reviews_data, # Simplification
        "comments": comments_data,
        "commits": mapped_commits,
        "author": {"login": pr["user"]["login"]},
        "statusCheckRollup": checks_rollup,
        "last_commit_author_login": last_commit_author,
        "last_commit_by_jules": _is_jules_login(last_commit_author),
    }


def get_base_sha(base_branch: str, repo_path: str = ".") -> str:
    """Get the current SHA of the base branch from GitHub API."""
    repo_info = get_repo_info()
    owner = repo_info["owner"]
    repo = repo_info["repo"]
    
    client = GitHubClient()
    if not client.token:
        return "Unknown"

    try:
        # API: GET /repos/{owner}/{repo}/branches/{branch}
        branch_data = client._get(f"repos/{owner}/{repo}/branches/{base_branch}")
        if branch_data and "commit" in branch_data:
            return branch_data["commit"]["sha"]
    except Exception:
        pass
        
    return "Unknown"


def _extract_session_id(branch: str, body: str) -> str | None:
    """Extract Jules session ID from branch name or PR body.

    Jules uses numeric session IDs (15-20 digits) embedded at the end of branch names.
    Branch pattern: {category}/{description}-{sessionID}
    Example: refactor/windowing-by-bytes-6277226227732204550
    """
    session_id = None

    # PRIMARY: Numeric session ID at end of branch (what Jules actually uses)
    # Pattern: 15-20 digits at the end (e.g., -6277226227732204550)
    match = re.search(r"-(\d{15,})$", branch)
    if match:
        return match.group(1)

    # FALLBACK: UUID pattern (for future compatibility, not currently used by Jules)
    uuid_match = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$", branch)
    if uuid_match:
        return uuid_match.group(1)

    # FALLBACK: Session ID in PR body
    if body:
        # Try jules.google.com URL (numeric ID)
        match = re.search(r"jules\.google\.com/task/(\d+)", body)
        if match:
            return match.group(1)

        # Try generic /task/ pattern (alphanumeric)
        match = re.search(r"/task/([a-zA-Z0-9-]+)", body)
        if match:
            return match.group(1)

        # Try /sessions/ pattern (alphanumeric)
        match = re.search(r"/sessions/([a-zA-Z0-9-]+)", body)
        if match:
            return match.group(1)

    return session_id


def _get_last_commit_author_login(commits: list[dict[str, Any]] | None) -> str | None:
    """Return the login of the last commit author, if available."""
    if not commits:
        return None

    last_commit = commits[-1] or {}
    
    # Try 'author' dict (standard GitHub API)
    author = last_commit.get("author")
    if isinstance(author, dict):
        login = author.get("login")
        if login:
            return login
    authors = last_commit.get("authors")
    if isinstance(authors, list):
        for entry in authors:
            if not isinstance(entry, dict):
                continue
            login = entry.get("login")
            if login:
                return login
            user = entry.get("user")
            if isinstance(user, dict):
                login = user.get("login")
                if login:
                    return login

    return None


def _is_jules_login(login: str | None) -> bool:
    """Check whether a login belongs to the Jules bot account."""
    if not login:
        return False
    return login in JULES_BOT_LOGINS


def _analyze_checks(checks_rollup: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """Analyze status checks to determine pass/fail status."""
    all_passed = True
    failed_check_names = []
    
    for check in checks_rollup:
        status = check.get("conclusion")
        if status in ["failure", "timed_out", "cancelled", "action_required"]:
            all_passed = False
            failed_check_names.append(check.get("name"))
            
    return all_passed, failed_check_names


def fetch_failed_logs_summary(pr_number: int, cwd: str = ".") -> str:
    """Fetch logs summary."""
    return ""


def fetch_full_ci_logs(pr_number: int, branch: str, repo_full: str, cwd: str = ".") -> str:
    """Fetch full CI logs for the latest failing workflow run on the branch."""
    if not branch or not repo_full:
        return ""
        
    client = GitHubClient()
    if not client.token:
        return ""

    try:
        runs_data = client._get(
            f"repos/{repo_full}/actions/runs",
            params={"branch": branch, "event": "pull_request", "per_page": 5}
        )
    except Exception:
        return ""

    if not runs_data:
        return ""

    workflow_runs = runs_data.get("workflow_runs", [])
    failing_runs = [run for run in workflow_runs if run.get("conclusion") == "failure"]

    if not failing_runs:
        return ""

    logs_sections: list[str] = []

    for run in failing_runs[:1]:
        run_id = run.get("id")
        run_url = run.get("html_url")
        workflow_name = run.get("name") or "Workflow"
        
        try:
            resp = client._get_raw(f"repos/{repo_full}/actions/runs/{run_id}/logs")
            if not resp:
                continue
                
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                log_files = [f for f in z.namelist() if f.endswith(".txt")]
                combined_log = ""
                for log_file in log_files:
                    with z.open(log_file) as f:
                        content = f.read().decode("utf-8", errors="replace")
                        if "failure" in content.lower() or "error" in content.lower():
                            combined_log += f"\n--- Log: {log_file} ---\n"
                            combined_log += content[-5000:]
                            
                if combined_log:
                    section = f"### {workflow_name} (Run ID: {run_id})\n"
                    if run_url:
                        section += f"**Full Log URL**: {run_url}\n\n"
                    section += f"```text\n{combined_log}\n```"
                    logs_sections.append(section)
                    
        except Exception:
            continue

    return "\n\n".join(logs_sections)


def get_repo_info() -> dict[str, str]:
    """Get owner and repo from environment or git."""
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER")
    repo_full = os.environ.get("GITHUB_REPOSITORY")

    if not owner or not repo_full:
        import subprocess
        try:
            # Try to get from git remote
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True
            )
            url = result.stdout.strip()
            # Handle various URL formats:
            # - https://github.com/owner/repo.git
            # - git@github.com:owner/repo.git
            # - http://local_proxy@127.0.0.1:PORT/git/owner/repo (proxy format)
            repo_detected = False

            # First, try to handle standard HTTP(S) GitHub URLs using proper URL parsing
            if url.startswith("http://") or url.startswith("https://"):
                try:
                    parsed = urlparse(url)
                    # Only treat as GitHub if the hostname is exactly github.com
                    if parsed.hostname == "github.com":
                        path_parts = parsed.path.rstrip("/").replace(".git", "").split("/")
                        # Expect path like /owner/repo
                        if len(path_parts) >= 3:
                            owner = path_parts[-2]
                            repo_full = f"{owner}/{path_parts[-1]}"
                            repo_detected = True
                except Exception:
                    # Fall through to proxy/generic handling below
                    pass

            # Next, handle SSH-style GitHub URLs: git@github.com:owner/repo(.git)
            if not repo_detected:
                ssh_match = re.match(r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", url)
                if ssh_match:
                    owner = ssh_match.group(1)
                    repo_full = f"{owner}/{ssh_match.group(2)}"
                    repo_detected = True

            if not repo_detected:
                # Handle proxy/generic URL format: .../git/owner/repo or .../owner/repo
                url_clean = url.replace(".git", "")
                # Try to find /git/owner/repo pattern first
                git_match = re.search(r"/git/([^/]+)/([^/]+)$", url_clean)
                if git_match:
                    owner = git_match.group(1)
                    repo_full = f"{owner}/{git_match.group(2)}"
                else:
                    # Fallback: last two path segments
                    parts = url_clean.split("/")
                    if len(parts) >= 2:
                        owner = parts[-2]
                        repo_full = f"{owner}/{parts[-1]}"
        except Exception:
            pass

    return {
        "owner": owner or "unknown",
        "repo": repo_full.split("/")[-1] if repo_full and "/" in repo_full else "unknown",
        "repo_full": repo_full or "unknown/unknown",
    }
