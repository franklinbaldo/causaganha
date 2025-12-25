#!/usr/bin/env python3
"""Comparison Script V1 vs V2.

Compares data counts and distributions between V1 (legacy) and V2 tables.
"""

import sys
from pathlib import Path

import structlog


# Ensure src is in pythonpath
sys.path.append(str(Path(__file__).parent.parent / "src"))

from causaganha.config import DB_PATH
from causaganha.storage.connection import get_connection


logger = structlog.get_logger()

def compare_data():
    logger.info("Starting V1 vs V2 comparison", db_path=DB_PATH)

    try:
        con = get_connection(DB_PATH)
        tables = con.list_tables()

        # Check if V1 tables exist
        has_v1 = "decisoes" in tables and "ratings" in tables
        if not has_v1:
            logger.warning("V1 tables (decisoes, ratings) not found. Cannot compare.")
            return

        # V1 Tables
        v1_decisions = con.table("decisoes")
        v1_ratings = con.table("ratings")

        # V2 Tables
        v2_analysis = con.table("analysis_results")
        v2_ratings = con.table("lawyer_ratings")

        # 1. Counts
        c_v1_dec = v1_decisions.count().execute()
        c_v2_res = v2_analysis.count().execute()

        c_v1_rat = v1_ratings.count().execute()
        c_v2_rat = v2_ratings.count().execute()

        logger.info("Counts Comparison",
                    v1_decisions=c_v1_dec,
                    v2_analysis=c_v2_res,
                    v1_ratings=c_v1_rat,
                    v2_ratings=c_v2_rat)

        # 2. Ratings Distribution (if data exists)
        if c_v1_rat > 0 and c_v2_rat > 0:
            avg_mu_v1 = v1_ratings.mu.mean().execute()
            avg_mu_v2 = v2_ratings.mu.mean().execute()

            logger.info("Ratings Mean Mu", v1=avg_mu_v1, v2=avg_mu_v2)

        else:
            logger.info("Insufficient data for ratings distribution comparison")

    except Exception:
        logger.exception("Comparison failed")
        sys.exit(1)

if __name__ == "__main__":
    compare_data()
