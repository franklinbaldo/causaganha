#!/usr/bin/env python3
"""Inspects PR check results to classify if it is purely a mechanical lint failure."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request


def fetch_json(url: str, token: str | None = None) -> dict:
    """Fetch JSON from a URL."""
    req = urllib.request.Request(url)  # noqa: S310
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError:
        sys.exit(1)


def classify_pr_checks(owner: str, repo: str, pr_number: int, token: str | None = None) -> str:
    """Classify the check runs for the latest commit of a PR."""
    pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    pr_data = fetch_json(pr_url, token)

    sha = pr_data.get("head", {}).get("sha")
    if not sha:
        return f"PR #{pr_number}: Could not determine head SHA."

    checks_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}/check-runs"
    checks_data = fetch_json(checks_url, token)

    return analyze_checks(pr_number, checks_data.get("check_runs", []))


def analyze_checks(pr_number: int, check_runs: list[dict]) -> str:
    """Analyze the check runs and return a classification message."""
    failures = []
    successes = []

    for check in check_runs:
        name = check.get("name", "")
        conclusion = check.get("conclusion")

        # "action_required" counts as failure/blocking, e.g. Kilo Code Review
        if conclusion in ("failure", "action_required", "timed_out", "cancelled"):
            failures.append(name)
        elif conclusion == "success":
            successes.append(name)

    if not failures:
        return f"PR #{pr_number}: all checks passed."

    # We want to know if ONLY mechanical/lint checks failed.
    # We consider "Kilo Code Review" as something that doesn't block "mechanical lint autofix".
    # And "CodeQL" action_required might happen, though usually it's success.
    # Let's consider mechanical failures to be just 'lint'.

    # Filter out Kilo Code Review and CodeQL from the list of things that block our autofix logic.
    # We just want to know if 'lint' failed and nothing else (other than Kilo/CodeQL).

    blocking_failures = [f for f in failures if f not in ("lint", "Kilo Code Review", "CodeQL")]

    if "lint" in failures and not blocking_failures:
        # We will dynamically mention them in the output if they are green.
        green_checks = [
            s.replace(" (tjro)", "")
            for s in successes
            if "docs" in s.lower() or "test" in s.lower() or "codeql" in s.lower()
        ]
        if green_checks:
            green_str = "/".join(sorted({g.lower() for g in green_checks}))
            return (
                f"PR #{pr_number}: mechanical lint failure; "
                f"{green_str} green; safe follow-up patch recommended"
            )
        return f"PR #{pr_number}: mechanical lint failure; safe follow-up patch recommended"

    # As per prompt context:
    #   - PR #437 is blocked by Kilo Code Review and lint.
    #   - We want to cover PR #437-style failures, where Kilo is blocked AND lint is blocked.
    # What if only Kilo is blocked?
    if not blocking_failures and "lint" not in failures:
         return f"PR #{pr_number}: no lint failure. Other blocked checks: {failures}"

    return f"PR #{pr_number}: logical or non-lint failures present: {failures}"


def main() -> None:
    """Execute the CLI program."""
    parser = argparse.ArgumentParser(
        description="Check if a PR has only a mechanical lint failure."
    )
    parser.add_argument("--pr", type=int, required=True, help="PR number to check")
    parser.add_argument(
        "--owner", type=str, default="franklinbaldo", help="Repository owner"
    )
    parser.add_argument(
        "--repo", type=str, default="causaganha", help="Repository name"
    )
    args = parser.parse_args()

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

    classify_pr_checks(args.owner, args.repo, args.pr, token)


if __name__ == "__main__":
    main()
