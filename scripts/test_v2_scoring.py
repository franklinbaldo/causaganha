#!/usr/bin/env python3
import asyncio
import argparse
import sys
from pathlib import Path
import structlog

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from causaganha.storage.connection import get_connection
from causaganha.storage.repository import IntimationRepository
from causaganha.pipeline.score import run_scoring

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

async def main():
    parser = argparse.ArgumentParser(description="Test V2 Scoring Pipeline")
    parser.add_argument("--limit", type=int, default=100, help="Number of cases to score")
    parser.add_argument("--db", type=str, default="test_collection.duckdb", help="Path to DuckDB file")
    args = parser.parse_args()

    db_path = Path(args.db)
    logger.info("setup", db=str(db_path))

    con = get_connection(str(db_path))
    # Schema should already exist
    repository = IntimationRepository(con)

    try:
        await run_scoring(
            repository=repository,
            limit=args.limit
        )
    except Exception as e:
        logger.exception("scoring_failed_toplevel", error=str(e))

    # Verify
    t = con.table("lawyer_ratings")
    try:
        count = t.count().execute()
        logger.info("verification", count=count)

        if count > 0:
            logger.info("sample", data=t.order_by(t.mu.desc()).limit(5).execute().to_dict(orient="records"))
    except Exception:
        logger.info("verification_no_table", msg="lawyer_ratings table might be empty or not created")

if __name__ == "__main__":
    asyncio.run(main())
