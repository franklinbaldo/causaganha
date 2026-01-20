#!/usr/bin/env python3
"""Daily Parquet export runner for scheduled execution.

This script is designed to be called by cron or systemd timer.
It exports yesterday's analyzed decisions to Parquet format and
uploads them to Internet Archive.

Exit codes:
    0: Success (all tribunals exported)
    1: Partial failure (some tribunals failed)
    2: Complete failure (no tribunals exported)
    3: Configuration error
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

import structlog

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from causaganha.v2.pipeline.export_orchestrator import ExportOrchestrator
from causaganha.v2.pipeline.ia_upload import InternetArchiveUploader, UploadConfig
from causaganha.v2.pipeline.parquet_export import ExportConfig, ParquetExporter
from causaganha.v2.storage.connection import get_connection


logger = structlog.get_logger()


def get_yesterday() -> str:
    """Get yesterday's date in YYYY-MM-DD format."""
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")


async def run_daily_export() -> int:
    """Run daily export and return exit code.

    Returns:
        0: All tribunals exported successfully
        1: Some tribunals failed
        2: All tribunals failed
        3: Configuration error
    """
    try:
        logger.info("daily_export_starting")

        # Initialize components
        con = get_connection()
        exporter = ParquetExporter(con, ExportConfig())
        uploader = InternetArchiveUploader(UploadConfig())
        orchestrator = ExportOrchestrator(con, exporter, uploader)

        # Export yesterday's data
        date = get_yesterday()
        logger.info("exporting_date", date=date)

        result = await orchestrator.run_daily_export(date, cleanup_files=True)

        # Log results
        logger.info(
            "daily_export_completed",
            date=result["date"],
            total_tribunals=result["total_tribunals"],
            successful=result["successful"],
            failed=result["failed"],
            total_rows=result["total_rows"],
            total_size_mb=result.get("total_size_mb", 0),
        )

        # Determine exit code
        if result["failed"] == 0:
            logger.info("daily_export_success", message="All tribunals exported successfully")
            return 0
        elif result["successful"] > 0:
            logger.warning(
                "daily_export_partial_failure",
                message=f"{result['failed']} tribunals failed",
                failures=result["failures"],
            )
            return 1
        else:
            logger.error(
                "daily_export_complete_failure",
                message="No tribunals exported successfully",
                failures=result["failures"],
            )
            return 2

    except Exception as e:
        logger.error("daily_export_error", error=str(e), exc_info=True)
        return 3


def main() -> int:
    """Main entry point."""
    try:
        exit_code = asyncio.run(run_daily_export())
        return exit_code
    except KeyboardInterrupt:
        logger.warning("daily_export_interrupted")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.error("daily_export_fatal_error", error=str(e), exc_info=True)
        return 3


if __name__ == "__main__":
    sys.exit(main())
