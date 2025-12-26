#!/usr/bin/env python3
"""Data Quality Validation Script for CausaGanha V2.

Runs comprehensive checks on the database content using DataValidator.
"""

import sys
from pathlib import Path

import structlog


# Ensure src is in pythonpath
sys.path.append(str(Path(__file__).parent.parent / "src"))

from causaganha.config import DB_PATH
from causaganha.storage.connection import get_connection
from causaganha.validation.validator import DataValidator


logger = structlog.get_logger()

def validate_data() -> None:
    logger.info("Starting data quality validation", db_path=DB_PATH)

    try:
        con = get_connection(DB_PATH)
        validator = DataValidator(con)

        has_errors = False

        # 1. Check Intimations
        intimation_report = validator.check_intimations()
        logger.info("Intimations check complete", **intimation_report)

        if intimation_report["invalid_links"] > 0:
            logger.warning("Found intimations with invalid links")

        # 2. Check Orphans
        orphans = validator.check_orphaned_analysis()
        if orphans:
            logger.error("Found orphaned analysis results", count=len(orphans), sample=orphans[:5])
            has_errors = True
        else:
            logger.info("No orphaned analysis results found")

        # 3. Check Ratings
        ratings_report = validator.check_ratings()
        logger.info("Ratings check complete", **ratings_report)

        if ratings_report["invalid_sigma"] > 0:
            logger.error("Found ratings with invalid sigma (<= 0)")
            has_errors = True

        if has_errors:
            logger.error("Validation failed with errors")
            sys.exit(1)

        logger.info("Validation passed - DATA OK")

    except Exception:
        logger.exception("Validation script failed")
        sys.exit(1)

if __name__ == "__main__":
    validate_data()
