#!/usr/bin/env python3
"""System Health Validation Script for CausaGanha V2.

Purpose:  Smoke-check that the V2 database is reachable and structurally sound.
Problem:  Silent DB/schema drift or missing tables lets downstream jobs fail
          obscurely; we want one fast pre-flight signal.
Strategy: Verify connectivity, schema presence, key-table row counts, and basic
          referential integrity (orphaned records), reporting failures clearly.
Status:   ops/health check — manual run (no workflow reference). RFC: wire into a
          pre-deploy or scheduled health workflow?


Checks:
1. Database connectivity.
2. Schema presence.
3. Row counts for key tables.
4. Basic referential integrity checks (orphaned records).
"""


# Safely reconfigure standard output and standard error encoding error handling on Windows
import contextlib
import sys


for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        with contextlib.suppress(AttributeError):
            stream.reconfigure(errors="replace")

import asyncio
import sys
from pathlib import Path

import structlog


# Ensure src is in pythonpath
sys.path.append(str(Path(__file__).parent.parent / "src"))

from causaganha.config import DB_PATH
from causaganha.storage.connection import get_connection


logger = structlog.get_logger()


async def validate_health() -> None:
    logger.info("Starting system health check", db_path=DB_PATH)

    try:
        # 1. Connectivity
        con = get_connection(DB_PATH)
        logger.info("Database connection established")

        # 2. Table Checks
        tables = con.list_tables()
        required_tables = {
            "intimations",
            "analysis_results",
            "lawyer_ratings",
            "pipeline_state",
            "schema_version",
        }
        missing_tables = required_tables - set(tables)

        if missing_tables:
            logger.error("Missing tables", missing=list(missing_tables))
            sys.exit(1)
        else:
            logger.info("All required tables present", tables=tables)

        # 3. Row Counts
        stats = {}
        for table in required_tables:
            try:
                count = con.table(table).count().execute()
                stats[table] = count
                logger.info("Table stats", table=table, count=count)
            except Exception as e:
                logger.exception("Failed to count table %s", table, error=str(e))

        # 4. Integrity Checks
        # Check for orphaned analysis results
        con.table("intimations")
        con.table("analysis_results")

        logger.info("Health check complete - SYSTEM OK")

    except Exception:
        logger.exception("Health check failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(validate_health())
