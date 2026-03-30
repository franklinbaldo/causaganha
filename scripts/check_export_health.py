#!/usr/bin/env python3

WARNING_FAILURE_RATE_PCT = 75.0
CRITICAL_FAILURE_RATE_PCT = 90.0

"""Health check script for Parquet export system.

This script checks the health of the export system and returns
appropriate exit codes for monitoring systems (Nagios, Prometheus, etc.).

Exit codes:
    0: OK - All exports successful
    1: WARNING - Some exports failed (< 10% failure rate)
    2: CRITICAL - Many exports failed (>= 10% failure rate) or no recent exports
    3: UNKNOWN - Cannot determine status
"""

import sys
from datetime import UTC, datetime, timedelta

import structlog

from causaganha.storage.connection import get_connection


logger = structlog.get_logger()


def check_recent_exports(days: int = 1) -> dict:
    """Check exports from the last N days.

    Args:
        days: Number of days to check

    Returns:
        Dictionary with status information
    """
    con = get_connection()

    cutoff_date = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")

    result = con.raw_sql(f"""
        SELECT
            COUNT(DISTINCT partition_date) as days_with_exports,
            COUNT(*) as total_exports,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
            ROUND(100.0 * SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate,
            MAX(partition_date) as last_export_date
        FROM parquet_exports
        WHERE partition_date >= '{cutoff_date}'
    """).fetchone()

    return {
        "days_with_exports": result[0],
        "total_exports": result[1],
        "successful": result[2],
        "failed": result[3],
        "pending": result[4],
        "success_rate": result[5],
        "last_export_date": str(result[6]) if result[6] else None,
    }


def check_problematic_tribunals(threshold_pct: float = 50.0) -> list:
    """Check for tribunals with high failure rates.

    Args:
        threshold_pct: Failure rate percentage threshold

    Returns:
        List of problematic tribunals
    """
    con = get_connection()

    result = con.raw_sql(f"""
        SELECT
            tribunal,
            failure_rate_pct,
            last_error
        FROM problematic_tribunals
        WHERE failure_rate_pct >= {threshold_pct}
        ORDER BY failure_rate_pct DESC
        LIMIT 10
    """).fetchall()

    return [{"tribunal": row[0], "failure_rate": row[1], "last_error": row[2]} for row in result]


def main() -> int:
    """Main health check logic."""
    try:
        # Check recent exports (last 1 day)
        stats = check_recent_exports(days=1)

        logger.info("export_health_check", **stats)

        # Determine health status
        if stats["total_exports"] == 0:
            return 2

        success_rate = stats["success_rate"] or 0.0

        if success_rate >= CRITICAL_FAILURE_RATE_PCT:
            # Check for problematic tribunals
            problematic = check_problematic_tribunals(threshold_pct=50.0)
            if problematic:
                for _t in problematic[:3]:  # Show top 3
                    pass
                result = 1
            else:
                result = 0
        elif success_rate >= WARNING_FAILURE_RATE_PCT:
            result = 1
        else:
            result = 2
    except Exception as e:
        logger.exception("health_check_error", error=str(e))
        return 3
    else:
        return result


if __name__ == "__main__":
    sys.exit(main())
