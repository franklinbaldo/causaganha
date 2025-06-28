#!/usr/bin/env python3
"""Run ruff formatting and linting."""

from __future__ import annotations

import subprocess
from typing import List

from src.utils.logging_config import setup_logging


def run_format() -> int:
    """Run ruff format."""
    result = subprocess.run(["uv", "run", "ruff", "format"])
    return result.returncode


def run_ruff(extra_args: List[str] | None = None) -> int:
    """Run ruff check with optional extra arguments."""
    cmd = ["uv", "run", "ruff", "check"]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(cmd)
    return result.returncode


def main() -> None:
    setup_logging()
    if run_format() != 0:
        raise SystemExit(1)
    if run_ruff() != 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
