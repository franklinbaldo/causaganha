#!/usr/bin/env python3
"""Create analytics tables if they do not exist."""

from __future__ import annotations

import duckdb
from pathlib import Path

from src.utils.logging_config import setup_logging, get_logger


def migrate(db_path: Path = Path("data/analytics.duckdb")) -> None:
    setup_logging()
    logger = get_logger(__name__)
    conn = duckdb.connect(str(db_path))
    logger.info("Running analytics migrations on %s", db_path)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_events (
            id INTEGER PRIMARY KEY,
            event_time TIMESTAMP,
            event_type TEXT,
            metadata TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_metrics (
            id INTEGER PRIMARY KEY,
            metric_date DATE,
            metric_name TEXT,
            metric_value DOUBLE
        )
        """
    )
    conn.close()
    logger.info("Analytics migrations completed")


if __name__ == "__main__":
    migrate()
