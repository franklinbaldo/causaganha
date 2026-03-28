#!/usr/bin/env python3
"""Generate kilo-queue.json containing PRs blocked only by Kilo Code Review."""

import json
import os
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


def get_kilo_queue() -> dict:  # noqa: C901, PLR0912, PLR0915
    """Fetch open PRs and filter those blocked ONLY by Kilo Code Review."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {
        "User-Agent": "causaganha-kilo-queue",
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = "https://api.github.com/repos/franklinbaldo/causaganha/pulls?state=open&per_page=100"
    req = urllib.request.Request(url, headers=headers)  # noqa: S310
    try:
        with urllib.request.urlopen(req) as r:  # noqa: S310
            prs = json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        print(f"Error fetching PRs: {e}")  # noqa: T201
        return {"metrics": {"total": 0, "avg_age_mins": 0, "max_age_mins": 0}, "prs": []}

    blocked_prs = []
    now = datetime.now(UTC)

    for pr in prs:
        sha = pr["head"]["sha"]
        url2 = f"https://api.github.com/repos/franklinbaldo/causaganha/commits/{sha}/check-runs"
        req2 = urllib.request.Request(url2, headers=headers)  # noqa: S310
        try:
            with urllib.request.urlopen(req2) as r:  # noqa: S310
                checks = json.loads(r.read()).get("check_runs", [])
        except Exception as e:  # noqa: BLE001
            print(f"Error fetching checks for PR #{pr['number']}: {e}")  # noqa: T201
            continue

        is_blocked_by_kilo = False
        other_checks_failed = False
        kilo_url = None
        kilo_completed_at = None

        for check in checks:
            name = check["name"]
            conclusion = check["conclusion"]
            status = check["status"]

            if name == "Kilo Code Review":
                if (
                    conclusion
                    in [
                        "action_required",
                        "failure",
                        "timed_out",
                        "cancelled",
                    ]
                    or status != "completed"
                ):
                    is_blocked_by_kilo = True
                    kilo_url = check["html_url"]
                    if check.get("completed_at"):
                        kilo_completed_at = check["completed_at"]
                    else:
                        kilo_completed_at = check.get("started_at")
            elif status != "completed" or (
                conclusion not in ["success", "skipped", "neutral", None]
            ):
                other_checks_failed = True

        if is_blocked_by_kilo and not other_checks_failed:
            age_mins = 0
            if kilo_completed_at:
                try:
                    completed_dt = datetime.strptime(
                        kilo_completed_at, "%Y-%m-%dT%H:%M:%SZ"
                    ).replace(tzinfo=UTC)
                    age_mins = int((now - completed_dt).total_seconds() / 60)
                except Exception:  # noqa: BLE001, S110
                    pass

            bucket = "fresh"
            if age_mins >= 120:  # noqa: PLR2004
                bucket = "stale"
            elif age_mins >= 60:  # noqa: PLR2004
                bucket = "warning"

            blocked_prs.append(
                {
                    "number": pr["number"],
                    "title": pr["title"],
                    "url": pr["html_url"],
                    "kilo_url": kilo_url,
                    "age_mins": age_mins,
                    "bucket": bucket,
                    "all_other_checks_green": True,
                }
            )

    total_blocked = len(blocked_prs)
    avg_age = sum(pr["age_mins"] for pr in blocked_prs) / total_blocked if total_blocked > 0 else 0
    max_age = max((pr["age_mins"] for pr in blocked_prs), default=0)

    # Sort PRs by age descending (oldest first)
    blocked_prs.sort(key=lambda x: x["age_mins"], reverse=True)

    return {
        "metrics": {
            "total": total_blocked,
            "avg_age_mins": round(avg_age, 1),
            "max_age_mins": max_age,
        },
        "prs": blocked_prs,
    }


def main() -> None:
    """Main execution entry point."""
    output_path = Path("dashboard/public/kilo-queue.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    queue_data = get_kilo_queue()
    output_path.write_text(json.dumps(queue_data, ensure_ascii=False, indent=2))
    print(f"Generated kilo-queue.json with {queue_data['metrics']['total']} PRs.")  # noqa: T201


if __name__ == "__main__":
    main()
