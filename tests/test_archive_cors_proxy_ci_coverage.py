"""``deployment/archive-cors-proxy`` must be exercised by CI, not just by hand.

Unlike ``deployment/relay-cf`` (dead infrastructure, never wired into any page —
see ``.wisk/knowledge/wiki/continuous-loop-operational-invariants.md``'s
seventeenth pattern), this Worker is the actual fix path for issue #1482:
``web/src/pages/explorador.astro`` reads ``PUBLIC_ARCHIVE_PROXY_BASE`` and
``web/src/lib/archiveProxyBase.ts``'s ``resolveArchiveDownloadBase`` builds the
`read_parquet(...)` base URL `DuckDBExplorer.svelte` uses from it. Its own
``test/index.test.js`` (15 cases: allowed item/file patterns, CORS headers,
Range forwarding, upstream-error handling) has existed since PR #1521 but no
workflow under ``.github/workflows/`` ever runs it — a regression in
``src/index.js`` (e.g. loosening ``ITEM_PATTERN``/``DOWNLOAD_PATH_PATTERN`` into
an open proxy, or dropping a CORS header) would merge with CI fully green.
Neither ``npm test`` (``@cloudflare/vitest-pool-workers``, a local ``workerd``
sandbox) nor ``npm run check`` (``wrangler deploy --dry-run``, bundles without
publishing) needs Cloudflare credentials, so there is no reason for this gap.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "test.yml"
WORKER_DIR = "deployment/archive-cors-proxy"


def _jobs() -> dict:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    return workflow["jobs"]


def _steps_running_in_worker_dir() -> list[dict]:
    steps: list[dict] = []
    for job in _jobs().values():
        job_cwd = job.get("defaults", {}).get("run", {}).get("working-directory")
        for step in job.get("steps", []):
            run = step.get("run")
            if run is None:
                continue
            step_cwd = step.get("working-directory", job_cwd)
            if (
                step_cwd == WORKER_DIR
                or f"--prefix {WORKER_DIR}" in run
                or f"cd {WORKER_DIR}" in run
            ):
                steps.append(step)
    return steps


def test_archive_cors_proxy_worker_tests_run_in_ci() -> None:
    runs = [step["run"] for step in _steps_running_in_worker_dir()]
    assert any("npm test" in run for run in runs), (
        f"No CI step under {WORKFLOW_PATH.relative_to(REPO_ROOT)} runs "
        f"`npm test` inside {WORKER_DIR} — its 15-case Vitest suite "
        "(test/index.test.js) is dead weight if nothing ever runs it."
    )


def test_archive_cors_proxy_worker_bundle_check_runs_in_ci() -> None:
    runs = [step["run"] for step in _steps_running_in_worker_dir()]
    assert any("wrangler deploy --dry-run" in run or "npm run check" in run for run in runs), (
        f"No CI step under {WORKFLOW_PATH.relative_to(REPO_ROOT)} runs "
        f"`{WORKER_DIR}`'s `check` script (`wrangler deploy --dry-run`) — a "
        "syntax error or bad import in src/index.js would only be caught at "
        "manual deploy time."
    )
