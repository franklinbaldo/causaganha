#!/usr/bin/env python3
"""Generate a compact Main Branch Health Digest.

Provides an operational summary of the recent health of `main`, using recent GitHub
workflow runs, so a maintainer can understand the current state of production.

Outputs to dashboard/public/cache/health-digest.json
"""

import datetime
import json
import urllib.request
import urllib.error
import os
from pathlib import Path

GITHUB_REPO = "franklinbaldo/causaganha"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "dashboard" / "public" / "cache"

def fetch_json(url: str) -> dict:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "causaganha-dashboard"
    }

    # Use GitHub token to avoid rate limits if available
    gh_token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if gh_token:
        headers["Authorization"] = f"Bearer {gh_token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Warning: Failed to fetch {url}: {e}")
        return None

def generate_health_digest() -> dict:
    digest = {"summary": "Unknown", "links": {}}

    # 1. Fetch latest commit on main
    commit_data = fetch_json(f"https://api.github.com/repos/{GITHUB_REPO}/commits/main")
    time_str = "??"
    if commit_data:
        last_commit_time = commit_data['commit']['author']['date']
        dt = datetime.datetime.strptime(last_commit_time, "%Y-%m-%dT%H:%M:%SZ")
        time_str = dt.strftime("%H:%M UTC")

    # 2. Fetch recent runs for main branch
    runs_data = fetch_json(f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs?branch=main&per_page=50")
    if not runs_data:
        digest["summary"] = f"main @ {time_str}: Failed to fetch run data"
        return digest

    workflows = {
        "Deploy Dashboard": "Deploy",
        "CodeQL": "CodeQL",
        "CI": "CI",
        "Collect ZIPs": "Collect",
        "monitor-collect": "monitor-collect"
    }

    status_map = {}
    url_map = {}

    # Find the latest completed run for each workflow
    for run in runs_data.get('workflow_runs', []):
        name = run.get('name', '')
        conclusion = run.get('conclusion')

        # We only care about completed runs (conclusion is not null)
        if not conclusion:
            continue

        key = None
        for w_name, short_name in workflows.items():
            if w_name in name or name == w_name:
                key = short_name
                break

        if 'monitor-collect' in name:
            key = 'monitor-collect'

        if key and key not in status_map:
            url_map[key] = run.get('html_url')

            if conclusion == 'failure':
                reason = ""
                jobs_url = run.get('jobs_url')
                if jobs_url:
                    jobs_data = fetch_json(jobs_url)
                    if jobs_data and jobs_data.get('jobs'):
                        for job in jobs_data.get('jobs', []):
                            if job.get('conclusion') == 'failure':
                                for step in job.get('steps', []):
                                    if step.get('conclusion') == 'failure':
                                        reason = f" ({step.get('name')})"
                                        break
                                if reason: break

                if not reason:
                    reason = " (workflow issue)"

                status_map[key] = f"failed{reason}"
            else:
                status_map[key] = "OK"

    # Enforce display order
    workflows_list = []
    parts = []
    for w in ["Deploy", "CodeQL", "CI", "Collect", "monitor-collect"]:
        if w in status_map:
            parts.append(f"{w} {status_map[w]}")
            workflows_list.append({
                "name": w,
                "status": status_map[w],
                "url": url_map[w]
            })

    if not parts:
        parts.append("No recent runs found")

    digest["summary"] = f"main @ {time_str}: " + ", ".join(parts)
    digest["time_str"] = time_str
    digest["workflows"] = workflows_list
    return digest

def main():
    print("Generating health digest...")
    digest = generate_health_digest()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "health-digest.json"

    with out_path.open("w") as f:
        json.dump(digest, f, separators=(",", ":"))

    print(f"Health digest saved to {out_path}")
    print(digest["summary"])

if __name__ == "__main__":
    main()
