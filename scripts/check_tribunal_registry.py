#!/usr/bin/env python3
"""Validate tribunal registry entries."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from src.tribunais import list_supported_tribunals  # type: ignore


def main() -> None:
    missing = []
    tribunais_dir = REPO_ROOT / "src" / "tribunais"
    for code in list_supported_tribunals():
        if not (tribunais_dir / code).exists():
            missing.append(code)
    if missing:
        print("Missing tribunal directories:", ", ".join(sorted(missing)))
        raise SystemExit(1)
    print(f"All {len(list_supported_tribunals())} tribunals registered correctly.")


if __name__ == "__main__":
    main()
