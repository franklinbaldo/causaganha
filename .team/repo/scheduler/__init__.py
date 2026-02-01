"""Jules Scheduler Package.

This package provides a simplified scheduler for Jules persona execution.
The scheduler:
1. Merges completed Jules PRs (drafts that pass CI)
2. Finds the next persona (round-robin from API state)
3. Renders the persona prompt with Jinja2
4. Creates a Jules session

Usage:
    from repo.scheduler import run_scheduler
    result = run_scheduler()
"""

from repo.scheduler.stateless import (  # noqa: F401
    JULES_BRANCH,
    SchedulerResult,
    discover_personas,
    merge_completed_prs,
    run_scheduler,
)
