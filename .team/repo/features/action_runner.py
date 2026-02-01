"""Action runner for persona-generated gh commands.

Personas can write shell scripts containing `gh` commands to files in
`.team/actions/new/`. This workflow scans for those files, executes
the commands, and moves completed files to `.team/actions/done/`.

This pattern allows personas to:
- Create GitHub issues (`gh issue create`)
- Add comments (`gh issue comment`, `gh pr comment`)
- Update labels (`gh issue edit --add-label`)
- Any other `gh` command

The workflow is simple: find files, execute commands, move files.
No complex parsing needed - the persona generates the actual command.

Example action file (.team/actions/new/maya-insight-001.sh):
```bash
#!/bin/bash
# Maya UX Insight: Improve button visibility

gh issue create \
  --repo franklinbaldo/egregora \
  --title "[HIGH] Improve button visibility on checkout page" \
  --label "ux,usability,severity:high,maya-generated" \
  --body "## Description
The submit button is hard to find.

## User Impact
Users abandon checkout.

## Recommendation
Use contrasting colors."
```
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ActionResult:
    """Result of executing an action file."""

    file_path: str
    success: bool
    output: str
    error: str | None = None


class ActionRunner:
    """Executes gh commands from persona action files.

    Scans `.team/actions/new/` for shell scripts, executes them,
    and moves completed files to `.team/actions/done/`.
    """

    def __init__(
        self,
        actions_dir: str | Path | None = None,
        dry_run: bool = False,
    ):
        """Initialize the action runner.

        Args:
            actions_dir: Path to .team/actions directory.
                        If None, uses default relative to repo root.
            dry_run: If True, don't actually execute commands.

        """
        if actions_dir is None:
            # Default to .team/actions relative to repo root
            self.actions_dir = Path(__file__).parent.parent.parent / "actions"
        else:
            self.actions_dir = Path(actions_dir)

        self.dry_run = dry_run
        self.new_dir = self.actions_dir / "new"
        self.done_dir = self.actions_dir / "done"

    def ensure_directories(self) -> None:
        """Ensure action directories exist."""
        self.new_dir.mkdir(parents=True, exist_ok=True)
        self.done_dir.mkdir(parents=True, exist_ok=True)

    def get_pending_actions(self) -> list[Path]:
        """Get list of pending action files.

        Returns:
            List of paths to action files in new/ directory.

        """
        self.ensure_directories()

        # Find all .sh files in new/
        action_files = sorted(self.new_dir.glob("*.sh"))
        return action_files

    def execute_action(self, action_file: Path) -> ActionResult:
        """Execute a single action file.

        Args:
            action_file: Path to the action shell script.

        Returns:
            ActionResult with execution status.

        """
        if self.dry_run:
            content = action_file.read_text()
            print(f"  [DRY RUN] Would execute: {action_file.name}")
            print(f"  Content preview: {content[:200]}...")
            return ActionResult(
                file_path=str(action_file),
                success=True,
                output="(dry run)",
            )

        try:
            # Execute the shell script
            result = subprocess.run(
                ["bash", str(action_file)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.actions_dir.parent.parent),  # Repo root
            )

            if result.returncode != 0:
                return ActionResult(
                    file_path=str(action_file),
                    success=False,
                    output=result.stdout,
                    error=result.stderr or f"Exit code: {result.returncode}",
                )

            return ActionResult(
                file_path=str(action_file),
                success=True,
                output=result.stdout,
            )

        except subprocess.TimeoutExpired:
            return ActionResult(
                file_path=str(action_file),
                success=False,
                output="",
                error="Command timed out after 60 seconds",
            )
        except Exception as e:
            return ActionResult(
                file_path=str(action_file),
                success=False,
                output="",
                error=str(e),
            )

    def move_to_done(self, action_file: Path, success: bool) -> None:
        """Move action file to done/ directory.

        Args:
            action_file: Path to the action file.
            success: Whether execution was successful.

        """
        if self.dry_run:
            print(f"  [DRY RUN] Would move {action_file.name} to done/")
            return

        # Add timestamp and status to filename
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        status = "ok" if success else "failed"
        new_name = f"{timestamp}-{status}-{action_file.name}"
        dest = self.done_dir / new_name

        shutil.move(str(action_file), str(dest))
        print(f"  Moved {action_file.name} -> done/{new_name}")

    def run_all(self) -> list[ActionResult]:
        """Execute all pending actions.

        Returns:
            List of ActionResult for each executed action.

        """
        results = []
        action_files = self.get_pending_actions()

        if not action_files:
            print("  No pending actions found")
            return results

        print(f"  Found {len(action_files)} pending action(s)")

        for action_file in action_files:
            print(f"  Executing: {action_file.name}")
            result = self.execute_action(action_file)
            results.append(result)

            if result.success:
                print(f"    ✓ Success: {result.output[:100] if result.output else '(no output)'}")
            else:
                print(f"    ✗ Failed: {result.error}")

            self.move_to_done(action_file, result.success)

        return results


def create_issue_action(
    repo: str,
    title: str,
    body: str,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
    persona_id: str = "persona",
) -> str:
    """Generate a shell script for creating a GitHub issue.

    This helper generates the complete shell script that personas
    can write to .team/actions/new/ for issue creation.

    Args:
        repo: Repository in owner/repo format.
        title: Issue title.
        body: Issue body (markdown).
        labels: Optional list of labels.
        assignees: Optional list of assignees.
        persona_id: ID of the persona creating the issue.

    Returns:
        Shell script content as a string.

    """
    labels_arg = ""
    if labels:
        labels_str = ",".join(labels)
        labels_arg = f'  --label "{labels_str}" \\\n'

    assignees_arg = ""
    if assignees:
        assignees_str = ",".join(assignees)
        assignees_arg = f'  --assignee "{assignees_str}" \\\n'

    # Escape body for shell
    escaped_body = body.replace('"', '\\"').replace('$', '\\$')

    script = f'''#!/bin/bash
# Action generated by {persona_id}
# Created: {datetime.now().isoformat()}

gh issue create \\
  --repo {repo} \\
  --title "{title}" \\
{labels_arg}{assignees_arg}  --body "{escaped_body}"
'''

    return script


def create_comment_action(
    repo: str,
    issue_number: int,
    body: str,
    persona_id: str = "persona",
) -> str:
    """Generate a shell script for adding a comment to an issue/PR.

    Args:
        repo: Repository in owner/repo format.
        issue_number: Issue or PR number.
        body: Comment body (markdown).
        persona_id: ID of the persona creating the comment.

    Returns:
        Shell script content as a string.

    """
    escaped_body = body.replace('"', '\\"').replace('$', '\\$')

    script = f'''#!/bin/bash
# Action generated by {persona_id}
# Created: {datetime.now().isoformat()}

gh issue comment {issue_number} \\
  --repo {repo} \\
  --body "{escaped_body}"
'''

    return script
