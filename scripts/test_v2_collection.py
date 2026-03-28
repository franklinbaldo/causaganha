from datetime import timezone

#!/usr/bin/env python3
import argparse
import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

import structlog


# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from causaganha.infrastructure.storage.connection import get_connection
from causaganha.infrastructure.storage.repositories.intimation import IntimationRepository
from causaganha.infrastructure.storage.schema import create_schema
from causaganha.integrations.pje.client import PJeAPIClient
from causaganha.pipeline.collect import run_collection


structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test V2 Collection Pipeline")
    parser.add_argument("--days", type=int, default=1, help="Number of days back to collect")
    parser.add_argument(
        "--db",
        type=str,
        default="test_collection.duckdb",
        help="Path to DuckDB file",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    logger.info("setup", db=str(db_path))

    con = get_connection(str(db_path))
    create_schema(con)
    repository = IntimationRepository(con)
    client = PJeAPIClient()

    today = datetime.now(timezone.utc).date()
    start_date = (today - timedelta(days=args.days)).isoformat()
    end_date = today.isoformat()

    logger.info("starting", start=start_date, end=end_date)

    try:
        await run_collection(
            repository=repository,
            client=client,
            start_date=start_date,
            end_date=end_date,
            courts=["TJRO"],
        )
    finally:
        await client.close()

    # Verify
    t = con.table("intimations")
    count = t.count().execute()
    logger.info("verification", count=count)

    if count > 0:
        logger.info("sample", data=t.limit(1).execute().to_dict(orient="records"))


if __name__ == "__main__":
    asyncio.run(main())
