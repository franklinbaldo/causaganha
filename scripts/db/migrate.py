#!/usr/bin/env python3
"""Run database migrations for CausaGanha."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.database import run_db_migrations
from src.utils.logging_config import setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute database migrations")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/causaganha.duckdb"),
        help="Path to DuckDB database",
    )
    parser.add_argument(
        "--migrations",
        type=Path,
        help="Path to migrations directory (defaults to 'migrations')",
    )

    args = parser.parse_args()
    setup_logging()

    try:
        run_db_migrations(args.db, args.migrations)
        logging.info("Database migrations completed successfully")
    except Exception as exc:
        logging.error("Migration failed: %s", exc)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
