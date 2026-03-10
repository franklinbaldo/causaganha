"""CausaGanha Data Pipeline - KISS Version.

Orchestrates pipeline steps sequentially, processing exactly ONE day per run.
Gathers date from --date flag or finds the next unconsolidated date.

Usage:
    # Process next date in backfill
    python scripts/pipeline/run.py

    # Process specific date
    python scripts/pipeline/run.py --date 2026-01-15
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path


# ── Immutable Data Types ──────────────────────────────────────


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for a pipeline run."""

    job: str
    date: str
    tribunal: str
    proxy_url: str
    scripts_dir: str
    repo_root: str
    deadline_seconds: float = 4800


@dataclass(frozen=True)
class StepResult:
    """Result of a single pipeline step."""

    name: str
    success: bool
    outputs: Mapping[str, str]
    duration_seconds: float


@dataclass(frozen=True)
class PipelineState:
    """State of the overall pipeline run."""

    results: tuple[StepResult, ...] = ()
    files_added: bool = False
    catalog_updated: bool = False
    start_time: float = field(default_factory=time.time)


# ── Constants ─────────────────────────────────────────────────

DEFAULT_PROXY_URL = "https://djen-proxy-mhgmawcn3a-rj.a.run.app"
STATE_FILE = Path("data/backfill-state.json")

# ── Date Discovery ───────────────────────────────────────────


def get_next_date(repo_root: str) -> str:
    """Find the next date to process (walking backward from today)."""
    state_path = Path(repo_root) / STATE_FILE
    cursor_date = None

    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
            cursor_date = state.get("cursor_date")
        except Exception:  # noqa: S110
            pass

    if cursor_date:
        # Move one day back from cursor
        next_d = date.fromisoformat(cursor_date) - timedelta(days=1)
    else:
        # Start from yesterday
        next_d = date.today() - timedelta(days=1)

    # Skip weekends
    while next_d.weekday() >= 5:
        next_d -= timedelta(days=1)

    return next_d.isoformat()


def update_cursor(repo_root: str, processed_date: str):
    """Update the cursor to the date just processed."""
    state_path = Path(repo_root) / STATE_FILE
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state = {"cursor_date": processed_date, "updated_at": datetime.now(UTC).isoformat()}
    state_path.write_text(json.dumps(state, indent=2))


# ── Execution ────────────────────────────────────────────────


def execute_step(name: str, cmd: list[str], cwd: str) -> StepResult:
    """Execute a single pipeline step."""
    print(f"\n{'=' * 60}\n  STEP: {name}\n{'=' * 60}\n  cmd: {' '.join(cmd)}\n")

    fd, output_file = tempfile.mkstemp(prefix=f"pipeline-{name}-", suffix=".txt")
    os.close(fd)

    env = {**os.environ, "GITHUB_OUTPUT": output_file, "PYTHONPATH": f"{cwd}:{Path(cwd) / 'src'}"}

    start_time = time.time()
    result = subprocess.run(cmd, env=env, cwd=cwd, check=False)
    duration = time.time() - start_time

    output_path = Path(output_file)
    outputs = {}
    if output_path.exists():
        for line in output_path.read_text().splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                outputs[k.strip()] = v.strip()
        output_path.unlink()

    success = result.returncode == 0
    print(f"\n  [{name}] {'OK' if success else 'FAILED'}")
    for k, v in outputs.items():
        print(f"    {k}={v}")

    return StepResult(name=name, success=success, outputs=outputs, duration_seconds=duration)


# ── Main ─────────────────────────────────────────────────────


def main():
    """Run the pipeline."""
    parser = argparse.ArgumentParser(description="CausaGanha Pipeline (KISS)")
    parser.add_argument("--job", default="all", choices=["all", "collect", "consolidate", "embed"])
    parser.add_argument("--date", default="")
    parser.add_argument("--proxy-url", default=os.getenv("DJEN_PROXY_URL", DEFAULT_PROXY_URL))
    args = parser.parse_args()

    repo_root = str(Path(__file__).parent.parent.parent)
    scripts_dir = str(Path(__file__).parent)

    target_date = args.date or get_next_date(repo_root)
    print(f"Pipeline starting | Job: {args.job} | Date: {target_date}")

    state = PipelineState()

    # 1. Collect
    if args.job in ("all", "collect"):
        cmd = [
            "uv",
            "run",
            "python",
            f"{scripts_dir}/collect.py",
            "--date",
            target_date,
            "--proxy-url",
            args.proxy_url,
        ]
        res = execute_step("collect", cmd, repo_root)
        state = PipelineState(
            results=(*state.results, res), files_added=res.outputs.get("files_added") == "true"
        )
        if not res.success:
            sys.exit(1)

    # 2. Consolidate
    if args.job in ("all", "consolidate"):
        cmd = ["uv", "run", "python", f"{scripts_dir}/consolidate.py", "--date", target_date]
        res = execute_step("consolidate", cmd, repo_root)
        state = PipelineState(
            results=(*state.results, res),
            files_added=state.files_added or res.outputs.get("files_added") == "true",
        )
        if not res.success:
            sys.exit(1)

    # 3. Embed
    if args.job in ("all", "embed"):
        cmd = ["uv", "run", "python", f"{scripts_dir}/embed.py", "--deadline", "10m"]
        res = execute_step("embed", cmd, repo_root)
        state = PipelineState(results=(*state.results, res), files_added=state.files_added)
        if not res.success:
            sys.exit(1)

    # 4. Catalog & Dashboard (only if files added or job is 'all')
    if args.job == "all" or state.files_added:
        execute_step(
            "catalog",
            ["uv", "run", "python", f"{repo_root}/scripts/generate_catalog.py", "--upload"],
            repo_root,
        )
        execute_step(
            "dashboard",
            ["uv", "run", "python", f"{repo_root}/scripts/generate_dashboard_cache.py"],
            repo_root,
        )

    # Update cursor if it was a backfill run
    if not args.date and args.job == "all":
        update_cursor(repo_root, target_date)

    print(f"\nPipeline complete. Files added: {state.files_added}")


if __name__ == "__main__":
    main()
