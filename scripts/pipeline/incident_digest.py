#!/usr/bin/env python3
"""Incident digest tool to summarize recurrent failures."""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


REPO = os.environ.get("GITHUB_REPOSITORY", "franklinbaldo/causaganha")
WORKFLOW = "collect-zips.yml"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
MAX_RUNS_TO_DISPLAY = 5


def api_get(path: str) -> Any:  # noqa: ANN401
    """Make an authenticated API request to GitHub."""
    url = f"https://api.github.com/repos/{REPO}/{path}"
    req = urllib.request.Request(url)  # noqa: S310
    req.add_header("Accept", "application/vnd.github.v3+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
    try:
        with urllib.request.urlopen(req) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"HTTPError fetching {url}: {e.code} {e.reason}\n")
        return None
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"Error fetching {url}: {e}\n")
        return None


def get_failed_steps_for_run(run_id: str) -> list[str]:
    """Retrieve the names of all steps that failed in a given run."""
    data = api_get(f"actions/runs/{run_id}/jobs")
    if not data or "jobs" not in data:
        return []

    failed_steps = []
    for job in data["jobs"]:
        failed_steps.extend(
            step.get("name") for step in job.get("steps", []) if step.get("conclusion") == "failure"
        )
    return failed_steps


def get_recent_failed_runs(limit: int = 10) -> list[dict[str, Any]]:
    """Get the most recent failed runs for the target workflow."""
    data = api_get(f"actions/workflows/{WORKFLOW}/runs?status=failure&per_page={limit}")
    if not data or "workflow_runs" not in data:
        return []
    return data["workflow_runs"]


def main() -> None:  # noqa: C901, PLR0912
    """Main entrypoint to summarize incident data and output it to the step summary."""
    current_run_id = os.environ.get("GITHUB_RUN_ID")

    recent_failed_runs = get_recent_failed_runs(10)

    # Check if current run is in the list of recent failed runs.
    if current_run_id and not any(str(r["id"]) == str(current_run_id) for r in recent_failed_runs):
        current_run_data = api_get(f"actions/runs/{current_run_id}")
        if current_run_data:
            # Insert at the beginning (most recent)
            recent_failed_runs.insert(0, current_run_data)

    runs_to_check = [
        {
            "id": str(r["id"]),
            "url": r.get("html_url", f"https://github.com/{REPO}/actions/runs/{r['id']}"),
            "created_at": r.get("created_at", ""),
        }
        for r in recent_failed_runs
    ]

    # Group runs by their specific failure signature
    signature_groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}

    for run in runs_to_check:
        failed_steps = get_failed_steps_for_run(run["id"])
        if not failed_steps:
            continue

        signature = tuple(failed_steps)
        if signature not in signature_groups:
            signature_groups[signature] = []
        signature_groups[signature].append(run)

    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    summary_lines = ["## 🚨 Recurring Incident Digest", ""]

    found_incidents = False
    for signature, runs in signature_groups.items():
        if not runs:
            continue

        found_incidents = True
        sig_str = " -> ".join(signature)

        if len(runs) > 1:
            summary_lines.append(f"### 🔥 Recurring Failure: `{sig_str}`")
            msg = f"**{len(runs)}** runs failed with this exact operational signature recently:"
            summary_lines.append(msg)
        else:
            summary_lines.append(f"### ⚠️ Isolated Failure: `{sig_str}`")
            summary_lines.append("This run failed with a unique signature:")

        summary_lines.append("")
        for r in runs[:MAX_RUNS_TO_DISPLAY]:
            date_str = r.get("created_at", "")
            summary_lines.append(f"- [Run {r['id']}]({r['url']}) ({date_str})")

        if len(runs) > MAX_RUNS_TO_DISPLAY:
            summary_lines.append(f"- ... and {len(runs) - MAX_RUNS_TO_DISPLAY} more earlier runs")
        summary_lines.append("")

    if not found_incidents:
        summary_lines.append("No clear failure signatures detected.")

    summary_text = "\n".join(summary_lines)
    sys.stdout.write(summary_text + "\n")

    if summary_file:
        try:
            with Path(summary_file).open("a") as f:
                f.write(summary_text + "\n")
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"Error writing to GITHUB_STEP_SUMMARY: {e}\n")


if __name__ == "__main__":
    main()
