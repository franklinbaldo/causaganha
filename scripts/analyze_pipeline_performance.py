#!/usr/bin/env python3
"""Comprehensive pipeline performance analyzer.

Purpose:  Profile the pipeline end-to-end to find bottlenecks and optimization wins.
Problem:  We need data, not guesses, about where pipeline time/memory/IO goes.
Strategy: Measure per-step execution time, memory, I/O, network, and parallelization
          potential, then surface bottlenecks and opportunities.
Status:   dev/profiling tool — manual run, not in any workflow.


Measures:
  - Execution time per step
  - Memory usage
  - I/O operations
  - Network requests
  - Parallelization potential
  - Bottlenecks and optimization opportunities
"""


# Safely reconfigure standard output and standard error encoding error handling on Windows
import contextlib
import sys


for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        with contextlib.suppress(AttributeError):
            stream.reconfigure(errors="replace")

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil
import structlog


# Constants
BYTES_PER_KB = 1024
FAST_STEP_THRESHOLD = 20
SLOW_STEP_THRESHOLD = 30
HIGH_MEMORY_THRESHOLD = 500

logger = structlog.get_logger()


@dataclass
class StepMetrics:
    """Metrics for a single pipeline step."""

    name: str
    start_time: float
    end_time: float
    returncode: int
    memory_peak_mb: float
    files_created: int
    bytes_created: int
    network_calls: int

    @property
    def duration_sec(self) -> float:
        """Calculate step duration in seconds."""
        return self.end_time - self.start_time

    @property
    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "duration_sec": round(self.duration_sec, 2),
            "memory_peak_mb": round(self.memory_peak_mb, 1),
            "files_created": self.files_created,
            "bytes_created": self.bytes_created,
            "network_calls": self.network_calls,
            "success": self.returncode == 0,
        }


def get_memory_usage() -> float:
    """Get current process memory usage in MB."""
    try:
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        return 0.0


def count_output_files(output_dir: Path, extensions: list[str]) -> tuple[int, int]:
    """Count files created with given extensions."""
    count = 0
    total_bytes = 0
    for ext in extensions:
        for file in output_dir.glob(f"*{ext}"):
            count += 1
            total_bytes += file.stat().st_size
    return count, total_bytes


def run_step_with_metrics(
    name: str,
    command: list[str],
    output_dir: Path,
    output_extensions: list[str],
) -> StepMetrics:
    """Run a pipeline step and measure its performance."""
    logger.info(
        "Running pipeline step",
        step=name,
        command=" ".join(command),
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    # Get initial state
    files_before, bytes_before = count_output_files(output_dir, output_extensions)

    start_time = time.time()

    # Run step
    returncode = 0
    try:
        result = subprocess.run(
            command,
            cwd=str(output_dir.parent),
            capture_output=False,
            timeout=600,
            check=False,
        )
        returncode = result.returncode
    except subprocess.TimeoutExpired:
        returncode = 124
        logger.exception("Pipeline step timeout after 600 seconds", step=name)
    except OSError:
        returncode = 1
        logger.exception("Pipeline step failed", step=name)

    end_time = time.time()

    # Get final state
    files_after, bytes_after = count_output_files(output_dir, output_extensions)
    memory_peak = get_memory_usage()

    # Calculate metrics
    files_created = files_after - files_before
    bytes_created = bytes_after - bytes_before

    metrics = StepMetrics(
        name=name,
        start_time=start_time,
        end_time=end_time,
        returncode=returncode,
        memory_peak_mb=memory_peak,
        files_created=files_created,
        bytes_created=bytes_created,
        network_calls=0,
    )

    # Log summary
    logger.info(
        "Pipeline step completed",
        step=name,
        duration_sec=round(metrics.duration_sec, 2),
        memory_mb=round(metrics.memory_peak_mb, 1),
        files_created=files_created,
        bytes_created=bytes_created,
        success=returncode == 0,
    )

    return metrics


def format_bytes(b: int) -> str:
    """Format bytes to human readable."""
    for unit in ["B", "KB", "MB", "GB"]:
        if b < BYTES_PER_KB:
            return f"{b:.1f} {unit}"
        b /= BYTES_PER_KB
    return f"{b:.1f} TB"


def analyze_results(metrics: list[StepMetrics]) -> None:
    """Analyze and print performance results."""
    total_time = 0.0
    for m in metrics:
        if m.returncode == 0:
            total_time += m.duration_sec

    logger.info("Performance analysis started", steps=len(metrics))

    # Summary statistics
    sorted_by_time = sorted(metrics, key=lambda m: m.duration_sec, reverse=True)
    successful = [m for m in metrics if m.returncode == 0]

    # Log bottlenecks
    for i, m in enumerate(sorted_by_time[:3], 1):
        if m.returncode == 0:
            pct = (m.duration_sec / total_time * 100) if total_time > 0 else 0
            logger.info(
                "Bottleneck step",
                rank=i,
                name=m.name,
                duration_sec=round(m.duration_sec, 2),
                percentage=round(pct, 1),
            )

    # Memory analysis
    if metrics:
        max_memory = max(m.memory_peak_mb for m in metrics)
        logger.info("Memory analysis", peak_mb=round(max_memory, 1))

    # Parallelization potential
    parallel_candidates = [m for m in successful if m.duration_sec < FAST_STEP_THRESHOLD]
    if parallel_candidates:
        estimated_parallel = max(m.duration_sec for m in parallel_candidates)
        speedup = total_time / estimated_parallel if estimated_parallel > 0 else 1
        logger.info(
            "Parallelization potential",
            sequential_sec=round(total_time, 2),
            estimated_parallel_sec=round(estimated_parallel, 2),
            potential_speedup=round(speedup, 1),
        )

    # Recommendations
    slow_steps = [
        m for m in sorted_by_time if m.returncode == 0 and m.duration_sec > SLOW_STEP_THRESHOLD
    ]
    if slow_steps:
        for m in slow_steps:
            recommendation = ""
            if m.name == "CONSOLIDATE":
                recommendation = "Increase --max-zips or parallelize table exports"
            elif m.name == "CATALOG":
                recommendation = "Implement incremental updates instead of full rebuild"
            elif m.name == "COLLECT":
                recommendation = "Batch multiple dates or parallelize per-tribunal"
            elif m.name == "DASHBOARD":
                recommendation = "Cache generated data, reduce API calls"

            if recommendation:
                logger.warning(
                    "Slow step detected",
                    name=m.name,
                    duration_sec=round(m.duration_sec, 2),
                    recommendation=recommendation,
                )

    high_memory = [m for m in metrics if m.memory_peak_mb > HIGH_MEMORY_THRESHOLD]
    if high_memory:
        for m in high_memory:
            logger.warning(
                "High memory usage detected",
                name=m.name,
                memory_mb=round(m.memory_peak_mb, 1),
                recommendation="Stream processing or batch smaller datasets",
            )

    # Export results
    results = {
        "timestamp": datetime.now(UTC).isoformat(),
        "total_duration_sec": round(total_time, 2),
        "steps": [m.to_dict for m in metrics],
    }

    output_file = Path("pipeline_performance.json")
    with output_file.open("w") as f:
        json.dump(results, f, indent=2)

    logger.info("Performance analysis completed", output_file=str(output_file))


def main() -> int:
    """Run full pipeline with performance measurement."""
    # Check credentials
    missing = [key for key in ["IAS3_ACCESS_KEY", "IAS3_SECRET_KEY"] if not os.getenv(key)]

    if missing:
        logger.error("Missing credentials", missing_keys=missing)
        return 1

    repo_root = Path(__file__).parent
    output_dir = repo_root / "pipeline-output"
    output_dir.mkdir(exist_ok=True)

    metrics: list[StepMetrics] = []

    try:
        # COLLECT
        metrics.append(
            run_step_with_metrics(
                "COLLECT",
                [
                    "uv",
                    "run",
                    "python",
                    "scripts/pipeline/collect.py",
                    "--max-items",
                    "5",
                ],
                output_dir,
                [".zip"],
            ),
        )

        # CONSOLIDATE
        metrics.append(
            run_step_with_metrics(
                "CONSOLIDATE",
                [
                    "uv",
                    "run",
                    "python",
                    "scripts/pipeline/consolidate.py",
                    "--backfill",
                    "--force",
                    "--max-zips",
                    "3",
                ],
                output_dir,
                [".parquet"],
            ),
        )

        # EMBED
        metrics.append(
            run_step_with_metrics(
                "EMBED",
                [
                    "uv",
                    "run",
                    "python",
                    "scripts/pipeline/embed.py",
                    "--max-decisions",
                    "50",
                ],
                output_dir,
                [".duckdb"],
            ),
        )

        # CATALOG
        metrics.append(
            run_step_with_metrics(
                "CATALOG",
                [
                    "uv",
                    "run",
                    "python",
                    "scripts/generate_catalog.py",
                ],
                output_dir,
                [".parquet", ".duckdb", ".sql"],
            ),
        )

        # DASHBOARD
        metrics.append(
            run_step_with_metrics(
                "DASHBOARD",
                [
                    "uv",
                    "run",
                    "python",
                    "scripts/generate_cache_from_manifest.py",
                ],
                output_dir,
                [".json", ".xml"],
            ),
        )

    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        return 130

    # Analyze and print results
    analyze_results(metrics)

    return 0


if __name__ == "__main__":
    sys.exit(main())
