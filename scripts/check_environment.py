#!/usr/bin/env python3
"""Check local development environment for CausaGanha.

This script verifies:
- Python version is at least 3.10
- `.venv` directory exists
- Required environment variables are set
- Project dependencies are satisfied via ``uv pip check``
- Analytics libraries are importable
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def check_python_version() -> bool:
    version_info = sys.version_info
    if version_info < (3, 10):
        logger.error(
            "Python 3.10 or higher is required. Current version: %s",
            sys.version.split()[0],
        )
        return False

    logger.info("✅ Python version %s", sys.version.split()[0])
    return True


def check_virtualenv() -> bool:
    venv_path = Path(".venv")
    if not venv_path.exists():
        logger.error(
            "Virtual environment '.venv' not found. Run 'uv venv && uv sync --dev && uv pip install -e .'"
        )
        return False

    logger.info("✅ Found virtual environment at %s", venv_path.resolve())
    return True


def check_env_vars() -> bool:
    required = ["GEMINI_API_KEY", "IA_ACCESS_KEY", "IA_SECRET_KEY"]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        logger.error(
            "Missing environment variables: %s", ", ".join(missing)
        )
        logger.error(
            "Create a .env file based on .env.example and set the required variables."
        )
        return False

    logger.info("✅ Required environment variables are set")
    return True


def run_uv_pip_check() -> bool:
    logger.info("Running 'uv pip check'...")
    result = subprocess.run(
        ["uv", "pip", "check"], capture_output=True, text=True
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        logger.error(output.strip())
        logger.error(
            "Dependency issues detected. Run 'uv sync --dev' to install or update packages."
        )
        return False

    logger.info(output.strip())
    logger.info("✅ Dependencies are satisfied")
    return True


def check_analytics_imports() -> bool:
    """Ensure analytics libraries can be imported."""
    required_modules = ["pandas", "duckdb", "openskill"]
    ok = True
    for mod in required_modules:
        try:
            __import__(mod)
            logger.info("✅ %s import successful", mod)
        except Exception as exc:
            logger.error("Failed to import %s: %s", mod, exc)
            ok = False
    return ok


def main() -> int:
    checks = [
        check_python_version(),
        check_virtualenv(),
        check_env_vars(),
        run_uv_pip_check(),
        check_analytics_imports(),
    ]

    if all(checks):
        logger.info("Environment check passed ✅")
        return 0

    logger.error("Environment check failed ❌")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
