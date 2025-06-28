#!/usr/bin/env python3
"""Display important environment variables for debugging."""

from __future__ import annotations

import os
from typing import List

from src.utils.logging_config import setup_logging, get_logger


KEY_VARS: List[str] = [
    "GEMINI_API_KEY",
    "IA_ACCESS_KEY",
    "IA_SECRET_KEY",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "ENABLED_TRIBUNALS",
    "DEFAULT_TRIBUNAL",
]


def main() -> None:
    setup_logging()
    logger = get_logger(__name__)
    for var in KEY_VARS:
        value = os.getenv(var, "<not set>")
        logger.info("%s=%s", var, value)


if __name__ == "__main__":
    main()
