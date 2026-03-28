#!/usr/bin/env python3
"""Generate a compact Incident Digest for failed GitHub Actions runs.

This script fetches the job steps from the GitHub API and extracts:
- Run ID and URL
- Failing step name
- Elapsed time until failure
- Final job/workflow conclusion
- Successful post-failure cleanup steps
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime


def fetch_job_data(repo: str, run_id: str, token: str) -> dict:
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs"
    headers = {
        "User-Agent": "causaganha-incident-digest",
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.URLError as e:
        print(f"Error fetching job data: {e}", file=sys.stderr)
        return {}


def format_digest(job: dict, run_id: str) -> str:
    lines = []
    lines.append(f"### 🚨 Incident Digest: {job.get('name', 'Job')} Failed")
    lines.append(f"**Run:** [{run_id}]({job.get('html_url', '')})")

    start_time_str = job.get("started_at")
    start_time = None
    if start_time_str:
        start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%SZ")

    failed_step = None
    cleanup_steps = []

    for step in job.get("steps", []):
        if step.get("conclusion") == "failure":
            failed_step = step
        elif failed_step and step.get("conclusion") == "success":
            # Any successful step after the failure is considered a cleanup/state-save step
            cleanup_steps.append(step.get("name"))

    if failed_step:
        lines.append(f"- **Failed Step:** `{failed_step.get('name')}`")
        if start_time:
            fail_time_str = failed_step.get("completed_at")
            if fail_time_str:
                fail_time = datetime.strptime(fail_time_str, "%Y-%m-%dT%H:%M:%SZ")
                elapsed = (fail_time - start_time).total_seconds()
                lines.append(f"- **Time to Failure:** {elapsed/60:.1f} minutes")

    lines.append(f"- **Job Conclusion:** `{job.get('conclusion')}`")

    if cleanup_steps:
        cleanup_str = ", ".join(f"`{s}`" for s in cleanup_steps)
        lines.append(f"- **Successful Post-Failure Steps:** {cleanup_str}")

    failed_name = failed_step.get("name") if failed_step else "unknown step"
    lines.append(
        f"\n> _The job failed at `{failed_name}`, "
        f"but {len(cleanup_steps)} recovery/cleanup steps ran successfully._"
    )

    return "\n".join(lines)


def main():
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

    if not repo or not run_id:
        # Fallback for local testing
        repo = os.environ.get("TEST_REPO", "franklinbaldo/causaganha")
        run_id = os.environ.get("TEST_RUN_ID")
        if not run_id:
            print(
                "Missing GITHUB_REPOSITORY or GITHUB_RUN_ID environment variables.",
                file=sys.stderr,
            )
            sys.exit(1)

    data = fetch_job_data(repo, run_id, token)

    digests = []
    for job in data.get("jobs", []):
        # A job currently executing will not have a conclusion, but its steps might have a failure
        has_failed_step = any(step.get("conclusion") == "failure" for step in job.get("steps", []))
        if job.get("conclusion") == "failure" or has_failed_step:
            digests.append(format_digest(job, run_id))

    if digests:
        output = "\n\n".join(digests) + "\n"
        print(output)

        step_summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
        if step_summary_file:
            with open(step_summary_file, "a") as f:
                f.write("\n" + output)


if __name__ == "__main__":
    main()
