#!/usr/bin/env python3
"""Verify tribunal discovery endpoints are reachable."""

from __future__ import annotations

import argparse
from datetime import date
from typing import List, Type

from src.utils.logging_config import setup_logging, get_logger, set_tribunal_code
from src.tribunais.tjro.discovery import TJRODiscovery

TRIBUNAL_DISCOVERY_MAP: dict[str, Type[TJRODiscovery]] = {
    "tjro": TJRODiscovery,
}


def check_tribunal(code: str) -> bool:
    """Check a single tribunal discovery."""
    discovery_cls = TRIBUNAL_DISCOVERY_MAP.get(code.lower())
    if not discovery_cls:
        raise ValueError(f"Unknown tribunal code: {code}")

    discovery = discovery_cls()
    set_tribunal_code(code)
    logger = get_logger(__name__)

    today = date.today()
    url = discovery.get_diario_url(today)
    if url:
        logger.info("%s discovery OK -> %s", code, url)
        return True
    logger.error("%s discovery failed for %s", code, today)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Check tribunal discovery endpoints")
    parser.add_argument("codes", nargs="*", help="Tribunal codes to check")
    args = parser.parse_args()

    setup_logging()

    codes: List[str] = args.codes if args.codes else list(TRIBUNAL_DISCOVERY_MAP)
    success = True
    for code in codes:
        if not check_tribunal(code):
            success = False
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
