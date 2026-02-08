#!/usr/bin/env python3
"""CausaGanha Data Pipeline - Single entry point.

Orchestrates pipeline steps with parallel initial execution:
  [collect | consolidate | embed] -> catalog -> dashboard-cache

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
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
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

INITIAL_STEPS: tuple[str, ...] = ("collect", "consolidate", "embed")

EMPTY_STATE = PipelineState()

DEFAULT_PROXY_URL = "https://djen-proxy-mhgmawcn3a-rj.a.run.app"


# ── Pure Functions: Config ────────────────────────────────────


def make_config(
    *,
    job: str,
    date: str,
    tribunal: str,
    proxy_url: str,
    scripts_dir: str,
    repo_root: str,
) -> PipelineConfig:
    """Build a validated PipelineConfig from raw inputs."""
    return PipelineConfig(
        job=job,
        date=date.strip() if date else "",
        tribunal=tribunal.strip() if tribunal else "",
        proxy_url=proxy_url,
        scripts_dir=scripts_dir,
        repo_root=repo_root,
    )


# ── Pure Functions: Command Building ──────────────────────────


def build_collect_cmd(config: PipelineConfig) -> tuple[str, ...]:
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
        "32",  # DEFINED BY STRESS TEST (2026-02-08): DO NOT INCREASE. IA S3 API REJECTS CONCURRENCY > 64.

        "--deadline",
        "1200s",
    )
    date_args: tuple[str, ...] = ("--date", config.date) if config.date else ()
    tribunal_args: tuple[str, ...] = ("--tribunal", config.tribunal) if config.tribunal else ()
    return base + date_args + tribunal_args


def build_consolidate_cmd(config: PipelineConfig) -> tuple[str, ...]:
    """Build the consolidate step command."""
    base: tuple[str, ...] = (
        "uv",
        "run",
        "python",
        f"{config.scripts_dir}/consolidate.py",
        "--deadline",
        "1200s",
        "--workers",
        "16",
    )
    mode_args: tuple[str, ...] = (
        ("--date", config.date) if config.date else ("--backfill", "--force")
    )
    return base + mode_args


def build_embed_cmd(config: PipelineConfig) -> tuple[str, ...]:
    """Build the embed step command."""
    return (
        "uv",
        "run",
        "python",
        f"{config.scripts_dir}/embed.py",
        "--deadline",
        "10m",
        "--max-decisions",
        "500",
    )


def build_catalog_cmd(config: PipelineConfig) -> tuple[str, ...]:
    """Build the catalog step command."""
    return (
        "uv",
        "run",
        "python",
        f"{config.repo_root}/scripts/generate_catalog.py",
        "--upload",
    )


def build_dashboard_cmd(config: PipelineConfig) -> tuple[str, ...]:
    """Build the dashboard-cache step command."""
    return (
        "uv",
        "run",
        "python",
        f"{config.repo_root}/scripts/generate_dashboard_cache.py",
    )


# Immutable registry: step name -> command builder
CMD_BUILDERS: Mapping[str, Callable[[PipelineConfig], tuple[str, ...]]] = {
    "collect": build_collect_cmd,
    "consolidate": build_consolidate_cmd,
    "embed": build_embed_cmd,
    "catalog": build_catalog_cmd,
    "dashboard": build_dashboard_cmd,
}


def build_step_cmd(step_name: str, config: PipelineConfig) -> tuple[str, ...]:
    """Look up and invoke the command builder for a step."""
    return CMD_BUILDERS[step_name](config)


# ── Pure Functions: Planning ──────────────────────────────────


def filter_initial_steps(job: str) -> tuple[str, ...]:
    """Determine which initial steps to run based on job selection."""
    if job == "all":
        return INITIAL_STEPS
    if job in INITIAL_STEPS:
        return (job,)
    return ()


def plan_initial_steps(config: PipelineConfig) -> tuple[StepPlan, ...]:
    """Plan the initial (unconditional) steps."""
    names = filter_initial_steps(config.job)
    return tuple(StepPlan(name=n, cmd=build_step_cmd(n, config)) for n in names)


def should_run_catalog(job: str, *, files_added: bool) -> bool:
    """Decide whether the catalog step should run.

    Always runs for 'all' job to ensure the manifest stays populated,
    even when no new files were added in this cycle. The catalog
    generation is idempotent and skips work when IA state hasn't changed.
    """
    return job in ("catalog", "all") or files_added


def should_run_dashboard(job: str, *, catalog_updated: bool) -> bool:
    """Decide whether the dashboard step should run.

    Always runs for 'all' job to keep the dashboard cache fresh,
    regardless of whether the catalog was updated in this cycle.
    """
    return job in ("dashboard", "all") or catalog_updated


def plan_catalog_step(
    config: PipelineConfig,
    state: PipelineState,
) -> tuple[StepPlan, ...]:
    """Conditionally plan the catalog step."""
    if should_run_catalog(config.job, files_added=state.files_added):
        return (StepPlan(name="catalog", cmd=build_step_cmd("catalog", config)),)
    return ()


def plan_dashboard_step(
    config: PipelineConfig,
    state: PipelineState,
) -> tuple[StepPlan, ...]:
    """Conditionally plan the dashboard step."""
    if should_run_dashboard(config.job, catalog_updated=state.catalog_updated):
        return (StepPlan(name="dashboard", cmd=build_step_cmd("dashboard", config)),)
    return ()


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
        results=state.results + (result,),
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

    # Step: Collect
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

    # Step: Consolidate
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

    # Step: Embed
    embed = get_result("embed")
    if embed:
        out = embed.outputs
        stats["steps"]["embed"] = {
            "texts_processed": int(out.get("embed_processed", 0)),
            "embeddings_saved": int(out.get("embed_saved", 0)),
            "failed": int(out.get("embed_failed", 0)),
            "duration_seconds": int(embed.duration_seconds),
        }

    # Step: Catalog
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


def execute_step(plan: StepPlan, cwd: str) -> StepResult:
    """Execute a single step via subprocess (impure: IO + subprocess)."""
    fd, output_file = tempfile.mkstemp(
        prefix=f"pipeline-{plan.name}-",
        suffix=".txt",
    )
    os.close(fd)

    step_env = {**os.environ, "GITHUB_OUTPUT": output_file}

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
        try:
            output_path.unlink()
        except OSError:
            pass

    success = result.returncode == 0

    sys.stdout.write(format_step_footer(plan.name, success=success, outputs=outputs))
    sys.stdout.write("\n")
    sys.stdout.flush()

    return StepResult(name=plan.name, success=success, outputs=outputs, duration_seconds=duration)


def execute_plans(
    plans: tuple[StepPlan, ...],
    state: PipelineState,
    cwd: str,
) -> PipelineState:
    """Execute steps sequentially, folding results into state (impure)."""
    for plan in plans:
        result = execute_step(plan, cwd)
        state = update_state(state, result)
    return state


def execute_plans_parallel(
    plans: tuple[StepPlan, ...],
    state: PipelineState,
    cwd: str,
) -> PipelineState:
    """Execute steps concurrently, folding results into state (impure).

    Used for initial steps (collect, consolidate, embed) which operate
    on different date cohorts and are independent of each other.
    """
    if len(plans) <= 1:
        return execute_plans(plans, state, cwd)
    with ThreadPoolExecutor(max_workers=len(plans)) as pool:
        futures = tuple(pool.submit(execute_step, plan, cwd) for plan in plans)
        results = tuple(f.result() for f in futures)
    for result in results:
        state = update_state(state, result)
    return state


def write_file(path: str, content: str) -> None:
    """Append content to a file (impure: file IO)."""
    with Path(path).open("a") as f:
        f.write(content)


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
    args = parser.parse_args()

    config = make_config(
        job=args.job,
        date=args.date,
        tribunal=args.tribunal,
        proxy_url=args.proxy_url,
        scripts_dir=str(Path(__file__).parent),
        repo_root=str(Path(__file__).parent.parent.parent),
    )

    sys.stdout.write(format_pipeline_header(config) + "\n")
    sys.stdout.flush()

    # Phase 1: initial steps run concurrently (independent date cohorts)
    initial_plans = plan_initial_steps(config)
    state = execute_plans_parallel(initial_plans, EMPTY_STATE, config.repo_root)

    # Phase 2: catalog (conditional on files_added)
    catalog_plans = plan_catalog_step(config, state)
    state = execute_plans(catalog_plans, state, config.repo_root)

    # Write run stats for dashboard consumption
    write_run_stats(config, state)

    # Phase 3: dashboard (conditional on catalog_updated)
    dashboard_plans = plan_dashboard_step(config, state)
    state = execute_plans(dashboard_plans, state, config.repo_root)

    # Output
    sys.stdout.write(format_pipeline_summary(state))
    sys.stdout.flush()

    if gh_output := os.getenv("GITHUB_OUTPUT"):
        write_file(gh_output, format_github_output(state))

    if gh_summary := os.getenv("GITHUB_STEP_SUMMARY"):
        write_file(gh_summary, format_github_summary(config.job, state))

    return 1 if has_failures(state) else 0


if __name__ == "__main__":
    sys.exit(main())
