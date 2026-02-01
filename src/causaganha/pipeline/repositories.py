"""Repository pattern for data access abstraction.

Provides a clean interface for database operations, making the orchestrator
testable with mock repositories. Follows dependency injection pattern.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import date, timedelta


logger = logging.getLogger(__name__)


class ExportRepository(ABC):
    """Abstract repository for export tracking operations."""

    @abstractmethod
    async def get_tribunals_for_date(self, partition_date: str) -> tuple[str, ...]:
        """Get list of tribunals with data for a date.

        Args:
            partition_date: Date in YYYY-MM-DD format

        Returns:
            Tuple of tribunal codes (sigla) with data for the date

        Raises:
            ValueError: If date has invalid format
        """

    @abstractmethod
    async def is_already_exported(self, partition_date: str, tribunal: str) -> bool:
        """Check if tribunal data for date was already exported.

        Args:
            partition_date: Date in YYYY-MM-DD format
            tribunal: Tribunal code (sigla)

        Returns:
            True if already exported with status='completed'
        """

    @abstractmethod
    async def record_pending(self, partition_date: str, tribunal: str) -> None:
        """Mark export as pending in the database.

        Args:
            partition_date: Date in YYYY-MM-DD format
            tribunal: Tribunal code (sigla)
        """

    @abstractmethod
    async def record_success(  # noqa: PLR0913
        self,
        partition_date: str,
        tribunal: str,
        ia_url: str,
        filename: str,
        row_count: int,
        size_mb: float,
    ) -> None:
        """Record successful export to database.

        Args:
            partition_date: Date in YYYY-MM-DD format
            tribunal: Tribunal code (sigla)
            ia_url: Internet Archive item URL
            filename: Parquet filename uploaded
            row_count: Number of rows exported
            size_mb: File size in megabytes
        """

    @abstractmethod
    async def record_failure(
        self,
        partition_date: str,
        tribunal: str,
        error: str,
    ) -> None:
        """Record failed export to database.

        Args:
            partition_date: Date in YYYY-MM-DD format
            tribunal: Tribunal code (sigla)
            error: Error message describing the failure
        """

    @abstractmethod
    async def purge_old_data(
        self,
        current_date: str,
        days_to_keep: int = 180,
    ) -> None:
        """Delete old intimations data after export (retention policy).

        Args:
            current_date: Current date in YYYY-MM-DD format (reference point)
            days_to_keep: Number of days of data to retain (default 180 = ~6 months)
        """


class DuckDBExportRepository(ExportRepository):
    """Concrete repository implementation using DuckDB via Ibis."""

    def __init__(self, db_connection) -> None:  # type: ignore[no-untyped-def]
        """Initialize repository with database connection.

        Args:
            db_connection: Ibis DuckDB backend connection
        """
        self.db = db_connection
        logger.debug("DuckDBExportRepository initialized")

    async def get_tribunals_for_date(self, partition_date: str) -> tuple[str, ...]:
        """Get tribunals with data for a date."""

        def _query() -> list:  # type: ignore[type-arg]
            intimations = self.db.table("intimations")
            result = (
                intimations.filter(intimations.data_disponibilizacao == partition_date)
                .distinct()
                .select("sigla_tribunal")
                .execute()
            )
            return list(result["sigla_tribunal"].unique())

        tribunals = await asyncio.to_thread(_query)
        logger.info(f"Found {len(tribunals)} tribunals for {partition_date}: {tribunals}")
        return tuple(tribunals)

    async def is_already_exported(self, partition_date: str, tribunal: str) -> bool:
        """Check if already exported."""

        def _query() -> bool:
            try:
                result = self.db.raw_sql(
                    """
                    SELECT COUNT(*) as cnt FROM parquet_exports
                    WHERE tribunal = ? AND partition_date = ? AND status = 'completed'
                    """,
                    [tribunal, partition_date],
                )
                return result[0]["cnt"] > 0
            except Exception as e:
                logger.warning(f"Could not check export status: {e}")
                return False

        already_exported = await asyncio.to_thread(_query)
        if already_exported:
            logger.info(f"Skipping {tribunal} ({partition_date}) - already exported")
        return already_exported

    async def record_pending(self, partition_date: str, tribunal: str) -> None:
        """Record as pending."""

        def _insert() -> None:
            self.db.raw_sql(
                """
                INSERT INTO parquet_exports
                (tribunal, partition_date, ia_item_id, ia_url, parquet_filename, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
                ON CONFLICT (tribunal, partition_date) DO UPDATE SET
                    status = 'pending',
                    uploaded_at = CURRENT_TIMESTAMP
                """,
                [tribunal, partition_date, "", "", ""],
            )

        await asyncio.to_thread(_insert)
        logger.debug(f"Recorded {tribunal} ({partition_date}) as pending")

    async def record_success(  # noqa: PLR0913
        self,
        partition_date: str,
        tribunal: str,
        ia_url: str,
        filename: str,
        row_count: int,
        size_mb: float,
    ) -> None:
        """Record successful export."""

        def _insert() -> None:
            self.db.raw_sql(
                """
                INSERT INTO parquet_exports
                (tribunal, partition_date, ia_item_id, ia_url, parquet_filename,
                 row_count, file_size_mb, uploaded_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'completed')
                ON CONFLICT (tribunal, partition_date) DO UPDATE SET
                    ia_url = excluded.ia_url,
                    parquet_filename = excluded.parquet_filename,
                    row_count = excluded.row_count,
                    file_size_mb = excluded.file_size_mb,
                    uploaded_at = CURRENT_TIMESTAMP,
                    status = 'completed'
                """,
                [tribunal, partition_date, ia_url, ia_url, filename, row_count, size_mb],
            )

        await asyncio.to_thread(_insert)
        logger.info(
            f"Recorded {tribunal} ({partition_date}) as completed: "
            f"{row_count} rows, {size_mb:.2f} MB",
        )

    async def record_failure(
        self,
        partition_date: str,
        tribunal: str,
        error: str,
    ) -> None:
        """Record failed export."""

        def _insert() -> None:
            self.db.raw_sql(
                """
                INSERT INTO parquet_exports
                (tribunal, partition_date, ia_item_id, ia_url, parquet_filename,
                 status, error_message)
                VALUES (?, ?, ?, ?, ?, 'failed', ?)
                ON CONFLICT (tribunal, partition_date) DO UPDATE SET
                    status = 'failed',
                    error_message = excluded.error_message,
                    uploaded_at = CURRENT_TIMESTAMP
                """,
                [tribunal, partition_date, "", "", "", error],
            )

        await asyncio.to_thread(_insert)
        logger.warning(f"Recorded {tribunal} ({partition_date}) as failed: {error}")

    async def purge_old_data(
        self,
        current_date: str,
        days_to_keep: int = 180,
    ) -> None:
        """Delete old intimations after export."""

        def _delete() -> int:
            cutoff_date = (
                date.fromisoformat(current_date) - timedelta(days=days_to_keep)
            ).isoformat()

            result = self.db.raw_sql(
                """
                DELETE FROM intimations
                WHERE data_disponibilizacao < ?
                AND (
                    SELECT COUNT(*) FROM parquet_exports
                    WHERE parquet_exports.tribunal = intimations.sigla_tribunal
                    AND parquet_exports.partition_date = intimations.data_disponibilizacao
                    AND parquet_exports.status = 'completed'
                ) > 0
                """,
                [cutoff_date],
            )
            return result.get("rows_deleted", 0) if isinstance(result, dict) else 0

        deleted = await asyncio.to_thread(_delete)
        logger.info(f"Purged {deleted} old intimations (older than {days_to_keep} days)")


class MockExportRepository(ExportRepository):
    """In-memory mock repository for testing."""

    def __init__(self, tribunals: tuple[str, ...] = ("TJSP", "TJRJ")) -> None:
        """Initialize mock with test data.

        Args:
            tribunals: Tuple of tribunal codes to return in queries
        """
        self.tribunals = tribunals
        self.pending: dict[tuple[str, str], bool] = {}
        self.exports: dict[tuple[str, str], dict[str, str | int | float]] = {}
        self.failures: dict[tuple[str, str], str] = {}

    async def get_tribunals_for_date(self, _partition_date: str) -> tuple[str, ...]:
        """Return fixed test data."""
        return self.tribunals

    async def is_already_exported(self, partition_date: str, tribunal: str) -> bool:
        """Check mock state."""
        key = (partition_date, tribunal)
        return key in self.exports and self.exports[key].get("status") == "completed"

    async def record_pending(self, partition_date: str, tribunal: str) -> None:
        """Record in mock."""
        key = (partition_date, tribunal)
        self.pending[key] = True

    async def record_success(  # noqa: PLR0913
        self,
        partition_date: str,
        tribunal: str,
        ia_url: str,
        filename: str,
        row_count: int,
        size_mb: float,
    ) -> None:
        """Record in mock."""
        key = (partition_date, tribunal)
        self.exports[key] = {
            "ia_url": ia_url,
            "filename": filename,
            "row_count": row_count,
            "size_mb": size_mb,
            "status": "completed",
        }

    async def record_failure(
        self,
        partition_date: str,
        tribunal: str,
        error: str,
    ) -> None:
        """Record in mock."""
        key = (partition_date, tribunal)
        self.failures[key] = error
        self.exports[key] = {"status": "failed", "error": error}

    async def purge_old_data(
        self,
        current_date: str,
        days_to_keep: int = 180,
    ) -> None:
        """Mock purge (no-op)."""
