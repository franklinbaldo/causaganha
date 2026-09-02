#!/usr/bin/env python3
"""Weekly watchdog for the daily canary itself (docs/SERVICE_OBJECTIVES.md).

`canary.yml` proves the deployed system works, but nothing proved that
`canary.yml` keeps running — a disabled trigger, a deleted workflow file, or
a GitHub-side scheduling hiccup would silence the canary without anyone
noticing, since the failure notification channel for canary.yml is
canary.yml itself.

This script is deliberately its own workflow (`canary-heartbeat.yml`) on a
different schedule, so it keeps checking even if canary.yml stops firing
entirely. It reads canary.yml's public run history from the GitHub Actions
API (no token needed, no side effects) and fails if the last confirmed
success is older than `CANARY_HEARTBEAT_THRESHOLD_HOURS`.

Exit 0 = canary.yml is still alive (warnings allowed). Exit 1 = it looks dead.

Usage:
    uv run python scripts/canary_heartbeat_check.py
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime

import structlog

from causaganha_mcp.workflow_runs import observe_workflow_runs
from scripts.canary_check import check_canary_heartbeat


log = structlog.get_logger()


def main(now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    observation = observe_workflow_runs("canary.yml")
    failures, warnings = check_canary_heartbeat(observation, now)

    for w in warnings:
        log.warning("canary_heartbeat.warning", message=w)
    for f in failures:
        log.error("canary_heartbeat.failure", message=f)

    if failures:
        print(
            f"CANARY HEARTBEAT FAILED: {len(failures)} failure(s), {len(warnings)} warning(s)",
            file=sys.stderr,
        )
        return 1

    print(f"CANARY HEARTBEAT OK ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
