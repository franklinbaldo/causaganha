#!/usr/bin/env python3
"""Verify V2 Collection Pipeline
Collects metadata from TJRO using V2 components and stores in DuckDB.
"""

import asyncio
import sys
from pathlib import Path

import structlog


# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from causaganha.v2.pipeline.collect import collect_metadata_for_court
from causaganha.v2.storage.connection import get_connection


# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()


async def main() -> None:
    """Run verification."""
    logger.info("verification_start")

    # Use a test database file
    db_path = "data/verify_v2.duckdb"
    con = get_connection(db_path)

    try:
        # Collect for TJRO, 1 day back
        result = await collect_metadata_for_court("TJRO", days_back=1)

        if result["status"] == "success":
            logger.info("collection_success", **result)

            # Verify DB content
            t = con.table("intimations")
            count = t.count().execute()
            logger.info("db_verification", count=count)

            if count > 0:
                sample = t.limit(1).execute().to_dict(orient="records")[0]
                logger.info("sample_record", id=sample["id"], tribunal=sample["sigla_tribunal"])

        else:
            error_msg = result.get("error", "")
            if "403" in error_msg or "Forbidden" in error_msg:
                logger.warning("geo_blocking_detected", error=error_msg)
                print(
                    f"⚠️ Geo-blocking detected: {error_msg}. This is expected in some environments."
                )
            else:
                logger.error("collection_failed_unexpectedly", error=error_msg)
                sys.exit(1)

    except Exception as e:
        logger.error("script_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
