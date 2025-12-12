#!/usr/bin/env python3
"""Helper to run the analytics pipeline."""

from __future__ import annotations

import subprocess

from causaganha_v1.utils.logging_config import get_logger, setup_logging


def main() -> None:
    setup_logging()
    logger = get_logger(__name__)

    cmd = ["uv", "run", "python", "src/ia_discovery.py", "--coverage-report"]
    logger.info("Running analytics pipeline: %s", " ".join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
