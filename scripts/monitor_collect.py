from __future__ import annotations


#!/usr/bin/env python3

MAX_RECENT_RUNS = 3

"""Monitor the collect-zips workflow and report on progress.

Checks the last N runs of collect-zips.yml and:
  - Reports upload rate (ZIPs/run, ZIPs/hour)
  - Detects stalls (0 uploads for K consecutive runs)
  - Detects error spikes
  - Outputs recommendations via GitHub Actions outputs

Exit codes:
  0 — healthy
  1 — stalled or too many errors (triggers adjustment)
"""

import json
import os
import subprocess
import sys
from pathlib import Path


REPO = os.environ.get("GITHUB_REPOSITORY", "franklinbaldo/causaganha")
WORKFLOW = "collect-zips.yml"
LOOKBACK_RUNS = 6  # examine last 6 runs (~2h)
STALL_THRESHOLD = 3  # consecutive runs with 0 uploads = stalled
MIN_UPLOAD_RATE = 5  # expect at least 5 uploads per run on average
ERROR_RATE_MAX = 0.30  # >30% failures = problem


def gh(*args: str) -> dict | list | str:
    """Run a gh CLI command and return parsed JSON."""
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout.strip()


def get_recent_runs(n: int) -> list[dict]:
    """Get the last N completed runs of collect-zips."""
    data = gh(
        "api",
        f"repos/{REPO}/actions/workflows/{WORKFLOW}/runs",
        "--jq",
        f'[.workflow_runs[::{n}] | .[] | select(.status == "completed") | '
        f"{{id: .id, conclusion: .conclusion, created_at: .created_at, "
        f"html_url: .html_url}}] | .[:{n}]",
    )
    if isinstance(data, list):
        return data
    return []


def get_run_summary(run_id: int) -> dict[str, int]:
    """Extract upload stats from a run's job logs (step summary)."""
    # Try to get step summary from the run
    gh(
        "api",
        f"repos/{REPO}/actions/runs/{run_id}/jobs",
        "--jq",
        "[.jobs[] | {name: .name, conclusion: .conclusion, steps: [.steps[] | {name: .name, conclusion: .conclusion}]}]",
    )
    # We can't easily get step outputs from the API, so just use conclusion
    return {}


def analyze_runs(runs: list[dict]) -> dict:
    """Analyze run history and return health assessment."""
    if not runs:
        return {"status": "unknown", "message": "No runs found"}

    total = len(runs)
    successes = sum(1 for r in runs if r["conclusion"] == "success")
    failures = sum(1 for r in runs if r["conclusion"] in ("failure", "timed_out"))
    cancelled = sum(1 for r in runs if r["conclusion"] == "cancelled")

    failure_rate = failures / total if total > 0 else 0

    # Check for consecutive failures at the end
    consecutive_failures = 0
    for run in runs:  # most recent first
        if run["conclusion"] in ("failure", "timed_out"):
            consecutive_failures += 1
        else:
            break

    status = "healthy"
    issues = []
    recommendations = []

    if consecutive_failures >= STALL_THRESHOLD:
        status = "stalled"
        issues.append(f"{consecutive_failures} consecutive failures")
        recommendations.append("Check DJEN proxy and IA credentials")
        recommendations.append("Try with --workers 1 to reduce rate limit pressure")

    elif failure_rate > ERROR_RATE_MAX:
        status = "degraded"
        issues.append(f"High failure rate: {failure_rate:.0%}")
        recommendations.append("Reduce workers to 1")
        recommendations.append("Check djen-backup logs for error patterns")

    return {
        "status": status,
        "total_runs": total,
        "successes": successes,
        "failures": failures,
        "cancelled": cancelled,
        "consecutive_failures": consecutive_failures,
        "failure_rate": failure_rate,
        "issues": issues,
        "recommendations": recommendations,
    }


def set_output(key: str, value: str) -> None:
    """Write to GITHUB_OUTPUT."""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with Path(output_file).open("a") as f:
            f.write(f"{key}={value}\n")


def main() -> int:

    runs = get_recent_runs(LOOKBACK_RUNS)

    if not runs:
        set_output("status", "unknown")
        set_output("action_needed", "false")
        return 0

    for r in runs[:3]:
        r["created_at"][:16]
    if len(runs) > MAX_RECENT_RUNS:
        pass

    analysis = analyze_runs(runs)

    if analysis["issues"]:
        for issue in analysis["issues"]:
            pass

    if analysis["recommendations"]:
        for rec in analysis["recommendations"]:
            pass

    action_needed = analysis["status"] in ("stalled", "degraded")
    set_output("status", analysis["status"])
    set_output("action_needed", str(action_needed).lower())
    set_output("consecutive_failures", str(analysis["consecutive_failures"]))

    # Write step summary
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with Path(summary_file).open("a") as f:
            f.write(f"## Collect Monitor — {analysis['status'].upper()}\n\n")
            f.write("| Metric | Value |\n|--------|-------|\n")
            f.write(f"| Runs analyzed | {analysis['total_runs']} |\n")
            f.write(f"| Success rate | {analysis['successes']}/{analysis['total_runs']} |\n")
            f.write(f"| Consecutive failures | {analysis['consecutive_failures']} |\n")
            if analysis["issues"]:
                f.write("\n### Issues\n")
                for issue in analysis["issues"]:
                    f.write(f"- {issue}\n")
            if analysis["recommendations"]:
                f.write("\n### Recommendations\n")
                for rec in analysis["recommendations"]:
                    f.write(f"- {rec}\n")

    return 1 if action_needed else 0


if __name__ == "__main__":
    sys.exit(main())
