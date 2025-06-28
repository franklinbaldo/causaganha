#!/usr/bin/env python3
"""Display important environment variables for debugging."""

from __future__ import annotations

import os
from typing import List


KEY_VARS: List[str] = [
    "GEMINI_API_KEY",
    "IA_ACCESS_KEY",
    "IA_SECRET_KEY",
    "LOG_LEVEL",
    "LOG_FORMAT",
]


def main() -> None:
    for var in KEY_VARS:
        value = os.getenv(var, "<not set>")
        print(f"{var}={value}")


if __name__ == "__main__":
    main()
