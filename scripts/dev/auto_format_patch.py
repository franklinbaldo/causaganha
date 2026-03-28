#!/usr/bin/env python3
"""
Auto-format Patch Bot for agent PRs in CausaGanha.

Goal:
When a PR created by an agent/Jules fails only because of `ruff format --check`,
provide the smallest operational path to fix it automatically or near-automatically.
"""

import sys
import subprocess
import re
import argparse
import json
import shlex
from typing import Set

def get_failed_run_for_pr(pr_number: str) -> str:
    """Gets the latest failed workflow run ID for a given PR."""
    try:
        pr_info_output = subprocess.check_output(
            ["gh", "pr", "view", pr_number, "--json", "headRefName"],
            text=True, stderr=subprocess.DEVNULL
        )
        pr_info = json.loads(pr_info_output)
        branch = pr_info.get("headRefName")

        if not branch:
            return ""

        run_output = subprocess.check_output(
            ["gh", "run", "list", "--branch", branch, "--status", "failure", "--json", "databaseId", "-L", "1"],
            text=True, stderr=subprocess.DEVNULL
        )
        run_data = json.loads(run_output)
        if not run_data:
            return ""

        return str(run_data[0]["databaseId"])
    except Exception:
        return ""

def get_pr_number_from_run(run_id: str) -> str:
    """Attempts to find the PR number associated with a specific run ID."""
    try:
        output = subprocess.check_output(
            ["gh", "run", "view", run_id, "--json", "headBranch"],
            text=True, stderr=subprocess.DEVNULL
        )
        data = json.loads(output)
        branch = data.get("headBranch", "")

        if not branch:
            return "Unknown"

        pr_output = subprocess.check_output(
            ["gh", "pr", "list", "--head", branch, "--json", "number"],
            text=True, stderr=subprocess.DEVNULL
        )
        pr_data = json.loads(pr_output)
        if pr_data and len(pr_data) > 0:
            return str(pr_data[0].get("number", "Unknown"))
    except Exception:
        pass
    return "Unknown"


def parse_logs(log_text: str) -> Set[str]:
    """Parses Ruff format output to extract files needing reformatting."""
    files_to_format = set()
    # Handle logs with ANSI escape codes or GitHub action timestamps
    # e.g., "2024-03-01T... Would reformat: file.py"
    # Ruff output format: "Would reformat: path/to/file.py"
    for line in log_text.splitlines():
        match = re.search(r'Would reformat:\s+([^\s\x1b]+)', line)
        if match:
            files_to_format.add(match.group(1).strip())
    return files_to_format

def main():
    parser = argparse.ArgumentParser(
        description="Auto-format Patch Bot: Resolves formatting-only CI failures for agent PRs"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pr", help="GitHub PR number to analyze")
    group.add_argument("--run-id", help="GitHub Actions Run ID to analyze")
    group.add_argument("--log-file", help="Local log file to parse (useful for debugging)")

    parser.add_argument("--apply", action="store_true", help="Run the suggested format command automatically")

    args = parser.parse_args()

    log_text = ""
    pr_number = "Unknown"

    if args.log_file:
        try:
            with open(args.log_file, 'r', encoding='utf-8') as f:
                log_text = f.read()
        except FileNotFoundError:
            print(f"Error: Could not find log file {args.log_file}")
            sys.exit(1)

    elif args.run_id:
        try:
            print(f"Fetching logs for run {args.run_id}...")
            log_text = subprocess.check_output(
                ["gh", "run", "view", args.run_id, "--log-failed"],
                text=True, stderr=subprocess.DEVNULL
            )
            pr_number = get_pr_number_from_run(args.run_id)
        except subprocess.CalledProcessError:
            print(f"Error: Could not fetch logs for run {args.run_id}. Ensure GitHub CLI is installed and authenticated.")
            sys.exit(1)

    elif args.pr:
        pr_number = args.pr
        run_id = get_failed_run_for_pr(args.pr)
        if not run_id:
            print(f"No failed workflow runs found for PR #{args.pr}.")
            sys.exit(0)

        try:
            print(f"Fetching logs for failed run {run_id}...")
            log_text = subprocess.check_output(
                ["gh", "run", "view", run_id, "--log-failed"],
                text=True, stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError:
            print(f"Error: Could not fetch logs for run {run_id}.")
            sys.exit(1)

    files_to_format = parse_logs(log_text)

    if not files_to_format:
        print("No formatting failures detected in the log (no 'Would reformat:' patterns found).")
        print("This failure might not be formatting-only, or the step log is unavailable.")
        sys.exit(0)

    files_list = sorted(list(files_to_format))
    file_count = len(files_list)

    pr_str = f"#{pr_number}" if pr_number != "Unknown" else "log"
    print(f"\nPR {pr_str} failed only on formatting; suggested fix targets {file_count} files.")

    cmd = ["uv", "run", "ruff", "format"] + files_list
    cmd_str = " ".join(shlex.quote(c) for c in cmd)

    print("\nMinimal corrective action path:")
    print(f"  {cmd_str}")

    if args.apply:
        print("\nApplying auto-format patch...")
        result = subprocess.run(cmd)
        if result.returncode == 0:
            print("\nFormatting successful! You can now commit and push the changes.")
        else:
            print("\nError applying format patch.")
            sys.exit(result.returncode)

if __name__ == "__main__":
    main()
