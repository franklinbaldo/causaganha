#!/usr/bin/env python3
"""Collect DJEN data and upload to Internet Archive.

Thin wrapper around the djen-backup package that preserves the pipeline
output contract (files_added=true/false in $GITHUB_OUTPUT).

The heavy lifting (DJEN API, IA upload, circuit breaker, gap detection)
is now handled by djen-backup. This script translates arguments and
reports results.

Usage:
    # Collect recent data (default: last 7 days)
    python scripts/pipeline/collect.py

    # Collect specific date
    python scripts/pipeline/collect.py --date 2026-01-27

    # Collect specific tribunal
    python scripts/pipeline/collect.py --date 2026-01-27 --tribunal TJSP
"""

import argparse
import os
import re
import subprocess
import sys

from scripts.pipeline.ia_s3 import parse_deadline


def build_djen_backup_cmd(args: argparse.Namespace) -> list[str]:
    """Build the djen-backup command from pipeline arguments."""
    cmd = ["uv", "run", "djen-backup"]

    # --date X becomes --start-date X --end-date X
    if args.date:
        cmd += ["--start-date", args.date, "--end-date", args.date]
    elif args.start_date and args.end_date:
        cmd += ["--start-date", args.start_date, "--end-date", args.end_date]
    # else: djen-backup defaults to backward scan from yesterday

    if args.tribunal:
        cmd += ["--tribunal", args.tribunal]

    # Convert deadline to minutes (djen-backup uses --deadline-minutes)
    deadline_sec = parse_deadline(args.deadline)
    deadline_min = max(1, deadline_sec // 60)
    cmd += ["--deadline-minutes", str(deadline_min)]

    if args.max_items > 0:
        cmd += ["--max-items", str(args.max_items)]

    cmd += ["--workers", str(args.workers)]

    return cmd


def build_subprocess_env(proxy_url: str) -> dict[str, str]:
    """Build environment for the djen-backup subprocess.

    djen-backup reads DJEN_PROXY_URL from the environment (no CLI flag),
    so we forward the --proxy-url argument as an env var.
    """
    env = {**os.environ}
    if proxy_url:
        env["DJEN_PROXY_URL"] = proxy_url
    return env


def parse_structlog_summary(output: str) -> dict[str, int]:
    """Extract upload stats from djen-backup's structlog console output.

    Looks for the 'run_complete' event which djen-backup logs with fields:
      uploaded, failed, absent_marked, skipped_deadline, skipped_circuit, total

    The output uses structlog ConsoleRenderer format:
      timestamp [level] run_complete  key1=value1 key2=value2 ...
    """
    stats = {"uploaded": 0, "failed": 0, "absent_marked": 0, "total": 0}
    for line in output.splitlines():
        if "run_complete" not in line:
            continue
        # Extract key=value pairs from the line
        for key in stats:
            match = re.search(rf"\b{key}=(\d+)", line)
            if match:
                stats[key] = int(match.group(1))
        break
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect DJEN data (via djen-backup)")
    parser.add_argument("--proxy-url", default="https://djen-proxy-mhgmawcn3a-rj.a.run.app")
    parser.add_argument("--date", help="Specific date (YYYY-MM-DD)")
    parser.add_argument("--start-date", help="Start of date range (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End of date range (YYYY-MM-DD, inclusive)")
    parser.add_argument("--tribunal", help="Specific tribunal (e.g., TJSP)")
    parser.add_argument("--max-items", type=int, default=0)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument(
        "--deadline", default="20m", help="Exit after this duration (e.g., 10m, 600s)"
    )
    args = parser.parse_args()

    # Validate arguments
    if args.date and (args.start_date or args.end_date):
        print("Error: Cannot use --date with --start-date/--end-date")
        return 1

    if (args.start_date and not args.end_date) or (args.end_date and not args.start_date):
        print("Error: Must specify both --start-date and --end-date")
        return 1

    cmd = build_djen_backup_cmd(args)
    env = build_subprocess_env(args.proxy_url)
    print("Collecting DJEN data via djen-backup...")
    print(f"  Command: {' '.join(cmd)}")
    print(f"  Proxy:   {args.proxy_url}")
    print()

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )

    # Replay captured output to stdout for pipeline logs
    if result.stdout:
        sys.stdout.write(result.stdout)
        sys.stdout.flush()

    # Parse stats from structlog output
    stats = parse_structlog_summary(result.stdout or "")
    files_added = stats["uploaded"] > 0 or stats["absent_marked"] > 0

    print()
    print("=" * 40)
    print("COLLECTION SUMMARY (via djen-backup)")
    print("=" * 40)
    print(f"  Uploaded: {stats['uploaded']}")
    print(f"  Absent:   {stats['absent_marked']}")
    print(f"  Failed:   {stats['failed']}")
    print(f"  Total:    {stats['total']}")
    print(f"\n  Files added: {files_added}")

    # Write pipeline output contract (same keys as before)
    if gh_output := os.getenv("GITHUB_OUTPUT"):
        with open(gh_output, "a") as f:
            f.write(f"files_added={'true' if files_added else 'false'}\n")
            f.write(f"collect_success={stats['uploaded'] + stats['absent_marked']}\n")
            f.write(f"collect_failed={stats['failed']}\n")
            f.write("collect_skipped=0\n")
            f.write("collect_downloaded_mb=0\n")

    return result.returncode


if __name__ == "__main__":
    exit(main())
