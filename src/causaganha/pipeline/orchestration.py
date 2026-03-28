from __future__ import annotations
from datetime import timezone

"""Pure orchestration logic for the export pipeline.

All functions here are pure (no side effects), making them fully testable
without mocks or external dependencies. Follows the pattern from
scripts/pipeline/run.py's pure functions.

Orchestration happens in 3 phases:
1. PLANNING (pure) - Build execution plan
2. EXECUTION (impure) - Run operations, collect results
3. AGGREGATION (pure) - Combine results into final output
"""


import logging
from datetime import date, timedelta

from .models import ExportPlan, ExportResult, TribunalExportResult


logger = logging.getLogger(__name__)


class PureOrchestrator:
    """Pure orchestration logic (testable, no I/O)."""

    @staticmethod
    def plan_export(
        partition_date: str,
        tribunals: tuple[str, ...],
        *,
        cleanup_files: bool = True,
    ) -> ExportPlan:
        """Pure: Build export plan from inputs.

        Args:
            partition_date: Date in YYYY-MM-DD format
            tribunals: Tuple of tribunal codes to export
            cleanup_files: Whether to delete local files after upload

        Returns:
            ExportPlan object (immutable)

        Raises:
            ValueError: If inputs are invalid
        """
        plan = ExportPlan(
            partition_date=partition_date,
            tribunals=tribunals,
            cleanup_files=cleanup_files,
        )
        plan.validate()  # Raises ValueError if invalid
        logger.debug("Planned export for %s tribunals on %s", len(tribunals), partition_date)
        return plan

    @staticmethod
    def add_tribunal_result(
        results: tuple[TribunalExportResult, ...],
        tribunal_result: TribunalExportResult,
    ) -> tuple[TribunalExportResult, ...]:
        """Pure: Add tribunal result to immutable tuple.

        This is immutable - returns a new tuple, doesn't modify input.

        Args:
            results: Existing tuple of results
            tribunal_result: New result to add

        Returns:
            New tuple with result appended (original unchanged)
        """
        tribunal_result.validate()
        return (*results, tribunal_result)

    @staticmethod
    def aggregate_results(
        partition_date: str,
        tribunal_results: tuple[TribunalExportResult, ...],
        duration_seconds: float,
    ) -> ExportResult:
        """Pure: Aggregate tribunal results into final export result.

        Args:
            partition_date: Date in YYYY-MM-DD format
            tribunal_results: Tuple of all tribunal export results
            duration_seconds: Total execution time in seconds

        Returns:
            ExportResult with aggregated statistics

        Raises:
            ValueError: If results are inconsistent
        """
        result = ExportResult(
            partition_date=partition_date,
            total_tribunals=len(tribunal_results),
            tribunal_results=tribunal_results,
            duration_seconds=duration_seconds,
        )
        result.validate()

        logger.info(
            "Aggregated results for %s: %s successful, %s failed, %s skipped (%s rows, %.2f MB)",
            partition_date,
            result.successful,
            result.failed,
            result.skipped,
            result.total_rows,
            result.total_size_mb,
        )
        return result

    @staticmethod
    def should_purge_data(
        results: ExportResult,
        _cleanup_interval_days: int = 180,
    ) -> bool:
        """Pure: Decide if cleanup should run based on results.

        Args:
            results: Export results
            cleanup_interval_days: Only purge if at least this many days of data exist

        Returns:
            True if any exports succeeded and cleanup should run
        """
        should_cleanup = results.successful > 0
        logger.debug("Should purge old data: %s", should_cleanup)
        return should_cleanup

    @staticmethod
    def get_yesterday_date() -> str:
        """Pure: Get yesterday's date in YYYY-MM-DD format.

        Returns:
            Yesterday's date as string
        """
        yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
        return yesterday.isoformat()
