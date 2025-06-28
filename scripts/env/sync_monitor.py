#!/usr/bin/env python3
"""Check Internet Archive sync status for environment debugging."""

from __future__ import annotations

import json

from src.ia_database_sync import IADatabaseSync
from src.utils.logging_config import setup_logging, get_logger


def main() -> None:
    setup_logging()
    logger = get_logger(__name__)
    sync = IADatabaseSync()
    status = sync.sync_status()
    logger.info("Sync status:\n%s", json.dumps(status, indent=2, default=str))


if __name__ == "__main__":
    main()
