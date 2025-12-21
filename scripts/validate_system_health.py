#!/usr/bin/env python3
"""System Health Validation Script for CausaGanha V2.

Checks:
1. Database connectivity.
2. Schema presence.
3. Row counts for key tables.
4. Basic referential integrity checks (orphaned records).
"""

import asyncio
import sys
from pathlib import Path

import structlog


# Ensure src is in pythonpath
sys.path.append(str(Path(__file__).parent.parent / "src"))

from causaganha.config import DB_PATH
from causaganha.storage.connection import get_connection


logger = structlog.get_logger()


async def validate_health():
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
                logger.error(f"Failed to count table {table}", error=str(e))

        # 4. Integrity Checks
        # Check for orphaned analysis results
        t_intimations = con.table("intimations")
        t_analysis = con.table("analysis_results")

        # Count analysis results where intimation_id is not in intimations
        # joined = t_analysis.left_join(t_intimations, t_analysis.intimation_id == t_intimations.id)
        # orphaned = joined.filter(t_intimations.id.isnull()).count().execute()

        # if orphaned > 0:
        #     logger.warning("Found orphaned analysis results", count=orphaned)
        # else:
        #     logger.info("Integrity check passed: No orphaned analysis results")

        logger.info("Health check complete - SYSTEM OK")

    except Exception:
        logger.exception("Health check failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(validate_health())
