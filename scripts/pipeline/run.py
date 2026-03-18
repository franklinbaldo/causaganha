#!/usr/bin/env python3
"""CausaGanha Data Pipeline - Single entry point.

Orchestrates pipeline steps sequentially:
  collect -> consolidate -> embed -> catalog -> dashboard-cache

GitHub Actions calls this script with minimal YAML. All pipeline
logic lives here for easier debugging and local development.

Design:
  - Pure functions for all logic (planning, command building, state)
  - Frozen dataclasses for immutable state
  - Tuple concatenation for command building (no mutable lists in core logic)
  - Impure boundary limited to execute_step / main

Usage:
    # Run all steps (default for scheduled runs)
    python scripts/pipeline/run.py

    # Run specific step
    python scripts/pipeline/run.py --job collect
    python scripts/pipeline/run.py --job consolidate --date 2026-01-15

    # Full pipeline with specific collect target
    python scripts/pipeline/run.py --date 2026-01-15 --tribunal TJSP
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


# ── Immutable Data Types ──────────────────────────────────────


@dataclass(frozen=True)
class PipelineConfig:
    """Pipeline configuration (immutable)."""

    job: str
    date: str
    tribunal: str
    proxy_url: str
    scripts_dir: str
    repo_root: str
    deadline_seconds: float = 4800  # 80m default (leaves buffer under 90m job)


@dataclass(frozen=True)
class StepPlan:
    """A planned pipeline step with its command."""

    name: str
    cmd: tuple[str, ...]


@dataclass(frozen=True)
class StepResult:
    """Result of executing a single step."""

    name: str
    success: bool
    outputs: Mapping[str, str]
    duration_seconds: float


@dataclass(frozen=True)
class PipelineState:
    """Accumulated pipeline state (immutable)."""

    results: tuple[StepResult, ...] = ()
    files_added: bool = False
    catalog_updated: bool = False
    start_time: float = field(default_factory=time.time)


# ── Constants ─────────────────────────────────────────────────

DATA_STEPS: tuple[str, ...] = ("collect", "consolidate", "embed")

ALL_STEPS: tuple[str, ...] = (*DATA_STEPS, "catalog", "dashboard")

DEFAULT_PROXY_URL = "https://djen-proxy-mhgmawcn3a-rj.a.run.app"

# Minimum seconds a step needs to be worth starting
MIN_STEP_SECONDS = 30


# ── Pure Functions: Config ────────────────────────────────────


def make_config(
    *,
    job: str,
    date: str,
    tribunal: str,
    proxy_url: str,
    scripts_dir: str,
    repo_root: str,
    deadline_seconds: float = 4800,
) -> PipelineConfig:
    """Build a validated PipelineConfig from raw inputs."""
    return PipelineConfig(
        job=job,
        date=date.strip() if date else "",
        tribunal=tribunal.strip() if tribunal else "",
        proxy_url=proxy_url,
        scripts_dir=scripts_dir,
        repo_root=repo_root,
        deadline_seconds=deadline_seconds,
    )


# ── Pure Functions: Command Building ──────────────────────────


def build_collect_cmd(config: PipelineConfig, *, deadline_s: int) -> tuple[str, ...]:
    """Build the collect step command."""
    base: tuple[str, ...] = (
        "uv",
        "run",
        "python",
        f"{config.scripts_dir}/collect.py",
        "--proxy-url",
        config.proxy_url,
        "--max-items",
        "10000",
        "--workers",
        "2",
        "--deadline",
        f"{deadline_s}s",
    )
    date_args: tuple[str, ...] = ("--date", config.date) if config.date else ()
    tribunal_args: tuple[str, ...] = ("--tribunal", config.tribunal) if config.tribunal else ()
    return base + date_args + tribunal_args


def build_consolidate_cmd(config: PipelineConfig, *, deadline_s: int) -> tuple[str, ...]:
    """Build the consolidate step command."""
    base: tuple[str, ...] = (
        "uv",
        "run",
        "python",
        f"{config.scripts_dir}/consolidate.py",
        "--deadline",
        f"{deadline_s}s",
        "--workers",
        "2",
    )
    mode_args: tuple[str, ...] = (
        ("--date", config.date) if config.date else ("--backfill", "--force")
    )
    return base + mode_args


def build_embed_cmd(config: PipelineConfig, *, deadline_s: int) -> tuple[str, ...]:
    """Build the embed step command."""
    return (
        "uv",
        "run",
        "python",
        f"{config.scripts_dir}/embed.py",
        "--deadline",
        f"{deadline_s}s",
        "--max-decisions",
        "500",
    )


def build_catalog_cmd(config: PipelineConfig, *, deadline_s: int) -> tuple[str, ...]:
    """Build the catalog step command."""
    _ = deadline_s  # catalog has no deadline flag
    return (
        "uv",
        "run",
        "python",
        f"{config.repo_root}/scripts/generate_catalog.py",
        "--upload",
    )


def build_dashboard_cmd(config: PipelineConfig, *, deadline_s: int) -> tuple[str, ...]:
    """Build the dashboard-cache step command."""
    _ = deadline_s  # dashboard has no deadline flag
    return (
        "uv",
        "run",
        "python",
        f"{config.repo_root}/scripts/generate_dashboard_cache.py",
    )


# Immutable registry: step name -> command builder
CMD_BUILDERS: Mapping[str, Callable[..., tuple[str, ...]]] = {
    "collect": build_collect_cmd,
    "consolidate": build_consolidate_cmd,
    "embed": build_embed_cmd,
    "catalog": build_catalog_cmd,
    "dashboard": build_dashboard_cmd,
}


def build_step_cmd(step_name: str, config: PipelineConfig, *, deadline_s: int) -> tuple[str, ...]:
    """Look up and invoke the command builder for a step."""
    return CMD_BUILDERS[step_name](config, deadline_s=deadline_s)


def remaining_seconds(state: PipelineState, config: PipelineConfig) -> int:
    """Seconds left in the pipeline deadline."""
    elapsed = time.time() - state.start_time
    return max(0, int(config.deadline_seconds - elapsed))


# ── Pure Functions: Planning ──────────────────────────────────


def should_run(step: str, config: PipelineConfig, state: PipelineState) -> bool:
    """Decide whether a pipeline step should run.

    Data steps (collect, consolidate, embed) run when explicitly requested
    or when job is 'all'.  Catalog and dashboard always run for 'all' and
    additionally trigger when upstream data changes.
    """
    if config.job == step:
        return True
    if config.job != "all":
        if step == "catalog":
            return state.files_added
        if step == "dashboard":
            return state.catalog_updated
        return False
    return True


# ── Pure Functions: Output Parsing ────────────────────────────


def parse_step_outputs(text: str) -> dict[str, str]:
    """Parse key=value pairs from step output text."""
    lines: tuple[str, ...] = tuple(line.strip() for line in text.splitlines())
    pairs: tuple[tuple[str, str, str], ...] = tuple(
        line.partition("=") for line in lines if "=" in line
    )
    return {key: value for key, _, value in pairs}


# ── Pure Functions: State Transitions ─────────────────────────


def update_state(state: PipelineState, result: StepResult) -> PipelineState:
    """Pure state transition: append result and update flags."""
    return PipelineState(
        results=(*state.results, result),
        files_added=state.files_added or result.outputs.get("files_added") == "true",
        catalog_updated=(state.catalog_updated or result.outputs.get("catalog_updated") == "true"),
        start_time=state.start_time,
    )


# ── Pure Functions: Formatting ────────────────────────────────


def format_step_header(name: str, cmd: tuple[str, ...]) -> str:
    """Format the header printed before a step runs."""
    sep = "=" * 60
    return f"\n{sep}\n  STEP: {name}\n{sep}\n  cmd: {' '.join(cmd)}\n"


def format_step_footer(name: str, *, success: bool, outputs: Mapping[str, str]) -> str:
    """Format the footer printed after a step completes."""
    status = "OK" if success else "FAILED"
    header = f"\n  [{name}] {status}"
    output_lines = tuple(f"    {k}={v}" for k, v in outputs.items())
    return "\n".join((header, *output_lines))


def format_pipeline_header(config: PipelineConfig) -> str:
    """Format the message printed when the pipeline starts."""
    lines: list[str] = [f"Pipeline starting  job={config.job}"]
    if config.date:
        lines.append(f"  date={config.date}")
    if config.tribunal:
        lines.append(f"  tribunal={config.tribunal}")
    return "\n".join(lines)


def format_pipeline_summary(state: PipelineState) -> str:
    """Format the final pipeline summary."""
    sep = "=" * 60
    return (
        f"\n{sep}\n"
        f"  Pipeline complete\n"
        f"{sep}\n"
        f"  files_added:     {state.files_added}\n"
        f"  catalog_updated: {state.catalog_updated}\n"
    )


def has_failures(state: PipelineState) -> bool:
    """Check whether any step in the pipeline failed."""
    return any(not r.success for r in state.results)


def format_github_output(state: PipelineState) -> str:
    """Format key=value pairs for $GITHUB_OUTPUT."""
    return (
        f"files_added={'true' if state.files_added else 'false'}\n"
        f"catalog_updated={'true' if state.catalog_updated else 'false'}\n"
    )


def build_comprehensive_stats(config: PipelineConfig, state: PipelineState) -> dict:
    """Build structured run stats from pipeline state for dashboard."""
    now = datetime.now(UTC)

    # Base structure
    stats = {
        "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "timestamp": now.isoformat(),
        "duration_seconds": int(time.time() - state.start_time),
        "status": "failed" if has_failures(state) else "success",
        "current_date": now.strftime("%Y-%m-%d"),
        "steps": {},
        "backfill": {},
        "tribunals": {},
        "internet_archive": {},
    }

    # Helper to find step result
    def get_result(name: str) -> StepResult | None:
        for r in state.results:
            if r.name == name:
                return r
        return None

    collect = get_result("collect")
    if collect:
        out = collect.outputs
        stats["steps"]["collect"] = {
            "success": int(out.get("collect_success", 0)),
            "failed": int(out.get("collect_failed", 0)),
            "skipped": int(out.get("collect_skipped", 0)),
            "tribunals_total": 96,  # Hardcoded for now, or derive from fetch
            "zips_downloaded_mb": float(out.get("collect_downloaded_mb", 0)),
            "duration_seconds": int(collect.duration_seconds),
        }

    consolidate = get_result("consolidate")
    if consolidate:
        out = consolidate.outputs
        stats["steps"]["consolidate"] = {
            "zips_processed": int(out.get("consolidate_zips", 0)),
            "records_total": int(out.get("consolidate_records", 0)),
            "parquets_generated": int(out.get("consolidate_parquets", 0)),
            "uploaded_mb": float(out.get("consolidate_uploaded_mb", 0)),
            "duration_seconds": int(consolidate.duration_seconds),
        }

    embed = get_result("embed")
    if embed:
        out = embed.outputs
        stats["steps"]["embed"] = {
            "texts_processed": int(out.get("embed_processed", 0)),
            "embeddings_saved": int(out.get("embed_saved", 0)),
            "failed": int(out.get("embed_failed", 0)),
            "duration_seconds": int(embed.duration_seconds),
        }

    catalog = get_result("catalog")
    if catalog:
        out = catalog.outputs
        stats["steps"]["catalog"] = {
            "manifest_updated": out.get("catalog_updated") == "true",
            "backfill_progress_pct": float(out.get("catalog_progress", 0)),
            "total_days_archived": int(out.get("catalog_dates", 0)),
            "total_days_target": 1826,  # 2021-2026
            "duration_seconds": int(catalog.duration_seconds),
        }

        # Populate Backfill details if available from catalog output (future improvement: make catalog output this JSON)
        # For now, we mock/estimate based on what we have or leave empty for the dashboard to handle gracefully
        # Ideally, generate_catalog.py should write a detailed JSON that we merge here.
        # Assuming catalog might output a backfill_stats.json in the future.

    return stats


def _format_step_metrics(outputs: Mapping[str, str]) -> str:
    """Format step outputs as a compact metrics string for the summary table."""
    parts = []
    for k, v in outputs.items():
        if k in ("files_added", "catalog_updated"):
            continue
        display_key = k.split("_", 1)[-1] if "_" in k else k
        parts.append(f"{display_key}: **{v}**")
    return ", ".join(parts) if parts else "---"


def format_github_summary(job: str, state: PipelineState) -> str:
    """Format rich markdown for $GITHUB_STEP_SUMMARY."""
    lines = [
        "## Pipeline Summary\n",
        f"**Job**: `{job}` | **Files added**: {state.files_added} | **Catalog updated**: {state.catalog_updated}\n",
        "### Step Results\n",
        "| Step | Status | Metrics |",
        "|------|--------|---------|",
    ]
    for result in state.results:
        icon = "&#x2705;" if result.success else "&#x274C;"
        metrics = _format_step_metrics(result.outputs)
        lines.append(f"| {result.name} | {icon} | {metrics} |")
    lines.append("")
    if state.catalog_updated:
        lines.append("[Catalog](https://archive.org/download/causaganha-catalog/catalog.duckdb)")
    return "\n".join(lines) + "\n"


def write_run_stats(config: PipelineConfig, state: PipelineState) -> None:
    """Write comprehensive run stats to dashboard/public/run-stats.json."""
    stats = build_comprehensive_stats(config, state)

    # Write to dashboard public dir
    dashboard_dir = Path(config.repo_root) / "dashboard" / "public"
    try:
        dashboard_dir.mkdir(parents=True, exist_ok=True)
        stats_path = dashboard_dir / "run-stats.json"

        with stats_path.open("w") as f:
            json.dump(stats, f, indent=2)

        sys.stdout.write(f"\nStats written to {stats_path}\n")
    except Exception as e:
        sys.stderr.write(f"\nFailed to write stats: {e}\n")


# ── Impure Boundary: Execution ────────────────────────────────


def run_step(plan: StepPlan, cwd: str) -> StepResult:
    """Run a single pipeline step as a subprocess."""
    fd, output_file = tempfile.mkstemp(
        prefix=f"pipeline-{plan.name}-",
        suffix=".txt",
    )
    os.close(fd)

    step_env = {
        **os.environ,
        "GITHUB_OUTPUT": output_file,
        "PYTHONPATH": f"{cwd}:{Path(cwd) / 'src'}:{os.environ.get('PYTHONPATH', '')}",
    }

    sys.stdout.write(format_step_header(plan.name, plan.cmd))
    sys.stdout.flush()

    start_time = time.time()
    result = subprocess.run(list(plan.cmd), env=step_env, cwd=cwd)
    duration = time.time() - start_time

    output_path = Path(output_file)
    try:
        outputs = parse_step_outputs(output_path.read_text())
    except FileNotFoundError:
        outputs = {}
    finally:
        with contextlib.suppress(OSError):
            output_path.unlink()

    success = result.returncode == 0

    sys.stdout.write(format_step_footer(plan.name, success=success, outputs=outputs))
    sys.stdout.write("\n")
    sys.stdout.flush()

    return StepResult(name=plan.name, success=success, outputs=outputs, duration_seconds=duration)


def append_to_file(path: str, content: str) -> None:
    """Append content to a file."""
    with Path(path).open("a") as f:
        f.write(content)


def _parse_deadline(s: str) -> float:
    """Parse '45m' or '2700s' to seconds."""
    if s.endswith("m"):
        return float(s[:-1]) * 60
    if s.endswith("s"):
        return float(s[:-1])
    return float(s)


# ── Entry Point ───────────────────────────────────────────────


def main() -> int:
    """Parse args, execute pipeline, write outputs (impure entry point)."""
    parser = argparse.ArgumentParser(
        description="CausaGanha Data Pipeline orchestrator",
    )
    parser.add_argument(
        "--job",
        default=os.getenv("INPUT_JOB", "all"),
        choices=["all", "collect", "consolidate", "embed", "catalog", "dashboard"],
        help="Which pipeline step to run (default: all)",
    )
    parser.add_argument(
        "--date",
        default=os.getenv("INPUT_DATE", ""),
        help="Specific date YYYY-MM-DD (optional, for collect/consolidate)",
    )
    parser.add_argument(
        "--tribunal",
        default=os.getenv("INPUT_TRIBUNAL", ""),
        help="Specific tribunal e.g. TJSP (optional, for collect)",
    )
    parser.add_argument(
        "--proxy-url",
        default=os.getenv("DJEN_PROXY_URL", DEFAULT_PROXY_URL),
        help="DJEN proxy URL",
    )
    parser.add_argument(
        "--deadline",
        default="80m",
        help="Pipeline deadline e.g. 45m, 2700s (default: 45m)",
    )
    args = parser.parse_args()

    config = make_config(
        job=args.job,
        date=args.date,
        tribunal=args.tribunal,
        proxy_url=args.proxy_url,
        scripts_dir=str(Path(__file__).parent),
        repo_root=str(Path(__file__).parent.parent.parent),
        deadline_seconds=_parse_deadline(args.deadline),
    )

    sys.stdout.write(format_pipeline_header(config) + "\n")
    sys.stdout.flush()

    state = PipelineState()

    for step in ALL_STEPS:
        if not should_run(step, config, state):
            continue
        budget = remaining_seconds(state, config)
        if budget < MIN_STEP_SECONDS:
            sys.stdout.write(f"\n  Skipping {step}: only {budget}s left in deadline\n")
            sys.stdout.flush()
            break
        plan = StepPlan(name=step, cmd=build_step_cmd(step, config, deadline_s=budget))
        result = run_step(plan, config.repo_root)
        state = update_state(state, result)

        # Snapshot stats after catalog so dashboard can consume them
        if step == "catalog":
            write_run_stats(config, state)

    sys.stdout.write(format_pipeline_summary(state))
    sys.stdout.flush()

    if gh_output := os.getenv("GITHUB_OUTPUT"):
        append_to_file(gh_output, format_github_output(state))

    if gh_summary := os.getenv("GITHUB_STEP_SUMMARY"):
        append_to_file(gh_summary, format_github_summary(config.job, state))

    return 1 if has_failures(state) else 0


if __name__ == "__main__":
    sys.exit(main())
