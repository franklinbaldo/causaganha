"""Verify V2 Collection Pipeline with real data from TJRO."""

import asyncio
import sys
from pathlib import Path
import structlog

# Add src to python path to ensure we can import the package
sys.path.append(str(Path(__file__).parent.parent / "src"))

from causaganha.v2.pipeline.collect import collect_metadata_for_court
from causaganha.v2.storage.connection import get_connection

logger = structlog.get_logger()

async def main() -> None:
    """Run the verification."""

    # Use a separate test database
    db_path = "data/verify_collection.duckdb"

    # Clean up previous run
    if Path(db_path).exists():
        Path(db_path).unlink()

    # Initialize connection (creates schema)
    con = get_connection(db_path)

    logger.info("Starting verification", court="TJRO", db=db_path)

    try:
        # Collect data for the last 1 day
        result = await collect_metadata_for_court("TJRO", days_back=1)

        logger.info("Collection result", result=result)

        if result["status"] != "success":
            error_msg = result.get("error", "")
            if "403" in error_msg:
                logger.warning(
                    "Collection failed with 403 Forbidden. "
                    "This usually indicates you are accessing the PJe API from a blocked region (e.g., outside Brazil). "
                    "Verification cannot proceed in this environment."
                )
                sys.exit(0)  # Exit gracefully

            logger.error("Collection failed", error=error_msg)
            sys.exit(1)

        # Verify data in DuckDB
        intimations = con.table("intimations").execute()
        count = len(intimations)

        logger.info("Verification", count=count)

        if count == 0:
            logger.warning("No intimations found. This might be expected if no new intimations were published in the last day.")
        else:
            logger.info("Sample intimation", sample=intimations.iloc[0].to_dict())

            # Check for lawyer associations
            lawyers = con.table("intimation_lawyers").execute()
            logger.info("Lawyer associations", count=len(lawyers))

    except Exception as e:
        logger.error("Verification failed with exception", error=str(e))
        sys.exit(1)
    finally:
        # Cleanup
        if Path(db_path).exists():
            Path(db_path).unlink()

if __name__ == "__main__":
    asyncio.run(main())
