#!/usr/bin/env python3
"""Comprehensive pipeline performance analyzer.

Measures:
  - Execution time per step
  - Memory usage
  - I/O operations
  - Network requests
  - Parallelization potential
  - Bottlenecks and optimization opportunities
"""

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog


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
        return self.end_time - self.start_time

    @property
    def to_dict(self) -> dict[str, Any]:
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
        import psutil

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
    print(f"\n{'=' * 70}")
    print(f"  STEP: {name}")
    print(f"{'=' * 70}")
    print(f"Command: {' '.join(command)}")
    print()

    output_dir.mkdir(parents=True, exist_ok=True)

    # Get initial state
    files_before, bytes_before = count_output_files(output_dir, output_extensions)
    memory_before = get_memory_usage()

    start_time = time.time()

    # Run step
    try:
        result = subprocess.run(
            command,
            cwd=str(output_dir.parent),
            capture_output=False,
            timeout=600,
            check=False,  # 10 minute timeout
        )
        returncode = result.returncode
    except subprocess.TimeoutExpired:
        returncode = 124
        print("TIMEOUT after 600 seconds")
    except Exception as e:
        returncode = 1
        print(f"ERROR: {e}")

    end_time = time.time()
    duration = end_time - start_time

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
        network_calls=0,  # TODO: trace network calls
    )

    # Print summary
    status = "✓ SUCCESS" if returncode == 0 else "✗ FAILED"
    print(f"\n{status}")
    print(f"  Duration: {metrics.duration_sec:.2f}s")
    print(f"  Memory: {metrics.memory_peak_mb:.1f} MB")
    print(f"  Files created: {files_created}")
    if bytes_created > 0:
        size_mb = bytes_created / 1024 / 1024
        print(f"  Data created: {size_mb:.1f} MB")

    return metrics


def format_bytes(b: int) -> str:
    """Format bytes to human readable."""
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def analyze_results(metrics: list[StepMetrics]) -> None:
    """Analyze and print performance results."""
    print(f"\n\n{'=' * 70}")
    print("  PERFORMANCE ANALYSIS")
    print(f"{'=' * 70}\n")

    # Summary table
    print("Step Performance:")
    print(f"  {'Step':<15} {'Duration':<10} {'Memory':<10} {'Output':<15}")
    print("-" * 50)

    total_time = 0
    for m in metrics:
        status = "✓" if m.returncode == 0 else "✗"
        output_size = format_bytes(m.bytes_created) if m.bytes_created > 0 else "—"
        print(
            f"  {status} {m.name:<13} {m.duration_sec:>6.2f}s    "
            f"{m.memory_peak_mb:>6.1f}MB   {output_size:<12}",
        )
        if m.returncode == 0:
            total_time += m.duration_sec

    print("-" * 50)
    print(f"  Total: {total_time:.2f}s\n")

    # Bottlenecks
    print("Bottlenecks (slowest steps):")
    sorted_by_time = sorted(metrics, key=lambda m: m.duration_sec, reverse=True)
    for i, m in enumerate(sorted_by_time[:3], 1):
        if m.returncode == 0:
            pct = (m.duration_sec / total_time * 100) if total_time > 0 else 0
            print(f"  {i}. {m.name}: {m.duration_sec:.2f}s ({pct:.1f}%)")

    # Memory analysis
    print("\nMemory usage:")
    max_memory = max(m.memory_peak_mb for m in metrics)
    print(f"  Peak: {max_memory:.1f} MB")

    # Parallelization potential
    print("\nParallelization potential:")
    sequential_time = sum(m.duration_sec for m in metrics if m.returncode == 0)
    parallel_candidates = [m for m in metrics if m.returncode == 0 and m.duration_sec < 20]
    if parallel_candidates:
        estimated_parallel = max(m.duration_sec for m in parallel_candidates)
        speedup = sequential_time / estimated_parallel if estimated_parallel > 0 else 1
        print(f"  Sequential: {sequential_time:.2f}s")
        print(f"  Parallel: ~{estimated_parallel:.2f}s (potential {speedup:.1f}x speedup)")

    # Recommendations
    print("\nOptimization recommendations:")
    slow_steps = [m for m in sorted_by_time if m.returncode == 0 and m.duration_sec > 30]
    if slow_steps:
        print("  ⚠ Slow steps (>30s):")
        for m in slow_steps:
            print(f"    - {m.name}: {m.duration_sec:.2f}s")
            if m.name == "CONSOLIDATE":
                print("      → Increase --max-zips or parallelize table exports")
            elif m.name == "CATALOG":
                print("      → Implement incremental updates instead of full rebuild")
            elif m.name == "COLLECT":
                print("      → Batch multiple dates or parallelize per-tribunal")
            elif m.name == "DASHBOARD":
                print("      → Cache generated data, reduce API calls")

    high_memory = [m for m in metrics if m.memory_peak_mb > 500]
    if high_memory:
        print("\n  ⚠ High memory usage (>500 MB):")
        for m in high_memory:
            print(f"    - {m.name}: {m.memory_peak_mb:.1f} MB")
            print("      → Stream processing or batch smaller datasets")

    # Export results
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_duration_sec": total_time,
        "steps": [m.to_dict for m in metrics],
    }

    output_file = Path("pipeline_performance.json")
    with output_file.open("w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Results saved to: {output_file}")


def main() -> int:
    """Run full pipeline with performance measurement."""
    # Check credentials
    missing = []
    for key in ["IAS3_ACCESS_KEY", "IAS3_SECRET_KEY"]:
        if not os.getenv(key):
            missing.append(key)

    if missing:
        print(f"ERROR: Missing credentials: {', '.join(missing)}")
        print("\nSet them before running:")
        print("  export IAS3_ACCESS_KEY='...'")
        print("  export IAS3_SECRET_KEY='...'")
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
                    "scripts/generate_dashboard_cache.py",
                ],
                output_dir,
                [".json", ".xml"],
            ),
        )

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130

    # Analyze and print results
    analyze_results(metrics)

    return 0


if __name__ == "__main__":
    sys.exit(main())
