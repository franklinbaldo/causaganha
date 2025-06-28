#!/usr/bin/env python3
"""Convenience wrapper to run the project test suite."""

from __future__ import annotations

import logging
import subprocess
from typing import List

from src.utils.logging_config import setup_logging


def run_pytest(extra_args: List[str] | None = None) -> int:
    """Run pytest via uv.

    Parameters
    ----------
    extra_args:
        Additional command line arguments for pytest.

    Returns
    -------
    int
        Exit code from pytest.
    """
    cmd = ["uv", "run", "pytest", "-q"]
    if extra_args:
        cmd.extend(extra_args)

    try:
        subprocess.run(cmd, check=True)
        return 0
    except subprocess.CalledProcessError as exc:
        logging.error("Tests failed with exit code %s", exc.returncode)
        return exc.returncode


def main() -> None:
    setup_logging()
    exit_code = run_pytest()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
