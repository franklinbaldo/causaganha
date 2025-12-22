#!/usr/bin/env python3
import asyncio
import argparse
import sys
from pathlib import Path
import structlog
import os

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from causaganha.analysis.analyzer import DecisionAnalyzer
from causaganha.services.document import DocumentService
from causaganha.storage.connection import get_connection
from causaganha.storage.repository import IntimationRepository
from causaganha.pipeline.analyze import run_analysis

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

async def main():
    parser = argparse.ArgumentParser(description="Test V2 Analysis Pipeline")
    parser.add_argument("--limit", type=int, default=5, help="Number of items to analyze")
    parser.add_argument("--db", type=str, default="test_collection.duckdb", help="Path to DuckDB file")
    args = parser.parse_args()

    db_path = Path(args.db)
    logger.info("setup", db=str(db_path))

    con = get_connection(str(db_path))
    # Schema should already exist from collection step
    repository = IntimationRepository(con)
    doc_service = DocumentService()

    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        logger.warning("no_google_api_key", msg="Analysis will likely fail without GOOGLE_API_KEY")

    analyzer = DecisionAnalyzer()

    try:
        await run_analysis(
            repository=repository,
            doc_service=doc_service,
            analyzer=analyzer,
            limit=args.limit
        )
    except Exception as e:
        logger.exception("analysis_failed_toplevel", error=str(e))

    # Verify
    t = con.table("analysis_results")
    try:
        count = t.count().execute()
        logger.info("verification", count=count)

        if count > 0:
            logger.info("sample", data=t.limit(1).execute().to_dict(orient="records"))
    except Exception:
        logger.info("verification_no_table", msg="analysis_results table might be empty or not created if no analyses ran")

if __name__ == "__main__":
    asyncio.run(main())
