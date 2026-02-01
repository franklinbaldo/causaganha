"""Tests for ensure_jules_branch() — verifies remote branch creation.

The Jules API requires the branch to exist on the remote before session
creation. These tests verify ensure_jules_branch() checks the remote
and pushes the branch when it's missing.
"""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from repo.scheduler.stateless import JULES_BRANCH, ensure_jules_branch


def _make_completed_process(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class TestEnsureJulesBranchRemoteMissing:
    """When the jules branch does NOT exist on the remote."""

    @patch("repo.scheduler.stateless.subprocess.run")
    def test_creates_and_pushes_branch(self, mock_run):
        """Branch is created locally and pushed to the remote."""
        # ls-remote returns empty stdout → branch missing on remote
        mock_run.return_value = _make_completed_process(returncode=0, stdout="")

        ensure_jules_branch()

        # Verify the sequence of git commands
        calls = mock_run.call_args_list
        commands = [c.args[0] if c.args else c.kwargs.get("args", []) for c in calls]

        # 1. fetch origin main
        assert commands[0] == ["git", "fetch", "origin", "main"]
        # 2. ls-remote to check remote
        assert commands[1] == ["git", "ls-remote", "--heads", "origin", JULES_BRANCH]
        # 3. delete stale local branch (best-effort)
        assert commands[2] == ["git", "branch", "-D", JULES_BRANCH]
        # 4. create branch from origin/main
        assert commands[3] == ["git", "branch", JULES_BRANCH, "origin/main"]
        # 5. push to remote
        assert commands[4] == ["git", "push", "-u", "origin", JULES_BRANCH]

    @patch("repo.scheduler.stateless.subprocess.run")
    def test_push_is_called_with_check(self, mock_run):
        """The push command uses check=True so failures are raised."""
        mock_run.return_value = _make_completed_process(returncode=0, stdout="")

        ensure_jules_branch()

        # Find the push call
        push_calls = [
            c for c in mock_run.call_args_list
            if c.args and c.args[0] == ["git", "push", "-u", "origin", JULES_BRANCH]
        ]
        assert len(push_calls) == 1
        assert push_calls[0].kwargs.get("check") is True

    @patch("repo.scheduler.stateless.subprocess.run")
    def test_ls_remote_failure_treated_as_missing(self, mock_run):
        """If ls-remote itself fails (network error), treat branch as missing."""

        def side_effect(cmd, **kwargs):
            if cmd == ["git", "ls-remote", "--heads", "origin", JULES_BRANCH]:
                return _make_completed_process(returncode=128, stdout="")
            return _make_completed_process()

        mock_run.side_effect = side_effect

        ensure_jules_branch()

        # Should still try to create and push
        commands = [c.args[0] for c in mock_run.call_args_list]
        assert ["git", "push", "-u", "origin", JULES_BRANCH] in commands


class TestEnsureJulesBranchRemoteExists:
    """When the jules branch already exists on the remote."""

    @patch("repo.scheduler.stateless.subprocess.run")
    def test_preserves_existing_branch(self, mock_run):
        """Branch is left as-is to preserve unmerged commits."""
        def side_effect(cmd, **kwargs):
            if cmd == ["git", "ls-remote", "--heads", "origin", JULES_BRANCH]:
                # ls-remote returns a ref → branch exists
                return _make_completed_process(
                    stdout=f"abc123\trefs/heads/{JULES_BRANCH}\n",
                )
            return _make_completed_process()

        mock_run.side_effect = side_effect

        ensure_jules_branch()

        commands = [c.args[0] for c in mock_run.call_args_list]

        # Should NOT try to create from scratch
        assert ["git", "branch", "-D", JULES_BRANCH] not in commands
        assert ["git", "push", "-u", "origin", JULES_BRANCH] not in commands

        # Should NOT reset the branch to main (would destroy unmerged commits)
        assert ["git", "branch", "-f", JULES_BRANCH, "origin/main"] not in commands
        assert ["git", "push", "--force-with-lease", "origin", JULES_BRANCH] not in commands

    @patch("repo.scheduler.stateless.subprocess.run")
    def test_no_push_when_branch_exists(self, mock_run):
        """No push operations when branch already exists on remote."""
        def side_effect(cmd, **kwargs):
            if cmd == ["git", "ls-remote", "--heads", "origin", JULES_BRANCH]:
                return _make_completed_process(
                    stdout=f"abc123\trefs/heads/{JULES_BRANCH}\n",
                )
            return _make_completed_process()

        mock_run.side_effect = side_effect

        ensure_jules_branch()

        push_calls = [
            c for c in mock_run.call_args_list
            if c.args and "push" in c.args[0]
        ]
        assert len(push_calls) == 0, "Should not push when branch already exists"

    @patch("repo.scheduler.stateless.subprocess.run")
    def test_only_runs_fetch_and_check(self, mock_run):
        """When branch exists, only fetch main and check remote — nothing else."""
        def side_effect(cmd, **kwargs):
            if cmd == ["git", "ls-remote", "--heads", "origin", JULES_BRANCH]:
                return _make_completed_process(
                    stdout=f"abc123\trefs/heads/{JULES_BRANCH}\n",
                )
            return _make_completed_process()

        mock_run.side_effect = side_effect

        ensure_jules_branch()

        commands = [c.args[0] for c in mock_run.call_args_list]

        # Only two git commands should run
        assert len(commands) == 2
        assert commands[0] == ["git", "fetch", "origin", "main"]
        assert commands[1] == ["git", "ls-remote", "--heads", "origin", JULES_BRANCH]
