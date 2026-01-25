"""Export Orchestration Module

Coordinates the daily Parquet export pipeline:
1. Query DuckDB for previous day's data
2. Export to Parquet (per tribunal)
3. Upload to Internet Archive
4. Record in database
5. Purge old data (>6 months)

Usage:
    orchestrator = ExportOrchestrator(db, exporter, uploader)
    await orchestrator.run_daily_export()
"""

import asyncio
import logging
from datetime import date, datetime, timedelta

from .ia_upload import InternetArchiveUploader
from .parquet_export import ParquetExporter


logger = logging.getLogger(__name__)


class ExportOrchestrator:
    """Orchestrates daily Parquet export pipeline."""

    def __init__(
        self,
        db_connection,
        parquet_exporter: ParquetExporter,
        ia_uploader: InternetArchiveUploader,
    ):
        """Initialize export orchestrator.

        Args:
            db_connection: Ibis DuckDB connection
            parquet_exporter: ParquetExporter instance
            ia_uploader: InternetArchiveUploader instance
        """
        self.db = db_connection
        self.exporter = parquet_exporter
        self.uploader = ia_uploader
        logger.info("ExportOrchestrator initialized")

    async def run_daily_export(
        self,
        partition_date: str | None = None,
        cleanup_files: bool = True,
    ) -> dict:
        """Run daily export for specified date (defaults to yesterday).

        Args:
            partition_date: Date in YYYY-MM-DD format (None = yesterday)
            cleanup_files: Remove local Parquet files after upload

        Returns:
            Export summary with statistics

        Raises:
            ValueError: If date has no data
        """
        # Default to yesterday
        if partition_date is None:
            partition_date = self._get_yesterday()

        logger.info(f"Starting daily export for {partition_date}")
        start_time = datetime.now()

        # Get tribunals with data for this date
        tribunals = await asyncio.to_thread(
            self.exporter._get_tribunals_for_date,
            partition_date,
        )

        if not tribunals:
            raise ValueError(f"No data found for date {partition_date}")

        logger.info(
            f"Found {len(tribunals)} tribunals with data for {partition_date}",
        )

        # Track results
        results = {
            "date": partition_date,
            "total_tribunals": len(tribunals),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_rows": 0,
            "total_size_mb": 0,
            "failures": [],
        }

        # Process each tribunal
        for tribunal in tribunals:
            try:
                success = await self._export_tribunal(
                    partition_date,
                    tribunal,
                    cleanup_files,
                )

                if success["skipped"]:
                    results["skipped"] += 1
                    logger.info(
                        f"Skipped {tribunal} (already exported)",
                    )
                else:
                    results["successful"] += 1
                    results["total_rows"] += success["row_count"]
                    results["total_size_mb"] += success["file_size_mb"]
                    logger.info(
                        f"✓ {tribunal}: {success['row_count']} rows, "
                        f"{success['file_size_mb']:.2f} MB",
                    )

            except Exception as e:
                results["failed"] += 1
                results["failures"].append({"tribunal": tribunal, "error": str(e)})
                logger.error(f"✗ {tribunal}: {e}", exc_info=True)

                # Record failure in database
                await self._record_export_failure(partition_date, tribunal, str(e))

        # Calculate duration
        duration = datetime.now() - start_time
        results["duration_seconds"] = duration.total_seconds()

        # Log summary
        success_rate = (
            100 * results["successful"] / results["total_tribunals"]
            if results["total_tribunals"] > 0
            else 0
        )

        logger.info(
            f"Export complete for {partition_date}: "
            f"{results['successful']}/{results['total_tribunals']} successful "
            f"({success_rate:.1f}%), "
            f"{results['total_rows']:,} rows, "
            f"{results['total_size_mb']:.1f} MB, "
            f"duration: {duration}",
        )

        # Purge old data if exports were successful
        if results["successful"] > 0:
            await self._purge_old_data(partition_date)

        return results

    async def _export_tribunal(
        self,
        partition_date: str,
        tribunal: str,
        cleanup_files: bool,
    ) -> dict:
        """Export single tribunal partition.

        Args:
            partition_date: Date in YYYY-MM-DD format
            tribunal: Tribunal code
            cleanup_files: Remove local file after upload

        Returns:
            Export result dictionary

        Raises:
            Exception: If export, upload, or recording fails
        """
        # Check if already exported
        if await self._already_exported(partition_date, tribunal):
            return {"skipped": True}

        # Mark as pending
        await self._record_export_pending(partition_date, tribunal)

        # 1. Export Comunicacoes to Parquet
        logger.info(f"Exporting {tribunal} for {partition_date}...")
        file_path, row_count = await self.exporter.export_day_tribunal(
            partition_date,
            tribunal,
        )

        file_size_mb = file_path.stat().st_size / (1024 * 1024)

        # 2. Upload Comunicacoes to Internet Archive
        logger.info(f"Uploading {file_path.name} to Internet Archive...")
        ia_url = await self.uploader.upload_parquet(
            file_path,
            tribunal,
            partition_date,
            file_size_mb,
            row_count,
        )

        # 3. Export & Upload Embeddings (if available)
        try:
            from causaganha.analysis.embedding_models import JINA_V4_1024
            from causaganha.storage.embedding_storage import get_embedding_storage

            emb_storage = get_embedding_storage(self.db)
            emb_filename = f"{tribunal}-{partition_date}-embeddings.parquet"
            emb_path = file_path.parent / emb_filename

            logger.info(f"Exporting embeddings for {tribunal} {partition_date}...")

            # Export using the new filtering capabilities
            # We assume JINA_V4_1024 is the primary model for now
            # In future we might want to iterate over active models
            try:
                emb_storage.export_to_parquet(
                    output_path=emb_path,
                    model=JINA_V4_1024,
                    tribunal=tribunal,
                    date=partition_date,
                )

                # Check if file has content
                if emb_path.exists() and emb_path.stat().st_size > 0:
                    emb_size_mb = emb_path.stat().st_size / (1024 * 1024)
                    emb_row_count = (
                        0  # ParquetExporter calculates this, but here we can read it or skip
                    )

                    logger.info(f"Uploading {emb_filename} to Internet Archive...")
                    await self.uploader.upload_parquet(
                        emb_path,
                        tribunal,
                        partition_date,
                        emb_size_mb,
                        # We don't track row count for embeddings in metadata yet effectively
                        # unless we read the file
                    )

                    if cleanup_files:
                        emb_path.unlink()

                else:
                    logger.warning("Embeddings export resulted in empty file, skipping upload.")

            except ValueError as e:
                # Table not found or no data - valid case if no embeddings generated yet
                logger.info(f"No embeddings found to export: {e}")

        except Exception as e:
            logger.warning(f"Failed to process embeddings export: {e}", exc_info=True)

        # 4. Export & Upload Lawyers
        try:
            logger.info(f"Exporting lawyers for {tribunal} {partition_date}...")
            lawyers_path, lawyers_rows = await self.exporter.export_lawyers(
                partition_date,
                tribunal,
            )

            if lawyers_rows > 0:
                lawyers_size_mb = lawyers_path.stat().st_size / (1024 * 1024)
                logger.info(f"Uploading {lawyers_path.name} to Internet Archive...")
                await self.uploader.upload_parquet(
                    lawyers_path,
                    tribunal,
                    partition_date,
                    lawyers_size_mb,
                    lawyers_rows,
                )
                if cleanup_files:
                    lawyers_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to export lawyers: {e}", exc_info=True)

        # 5. Export & Upload Parties
        try:
            logger.info(f"Exporting parties for {tribunal} {partition_date}...")
            parties_path, parties_rows = await self.exporter.export_parties(
                partition_date,
                tribunal,
            )

            if parties_rows > 0:
                parties_size_mb = parties_path.stat().st_size / (1024 * 1024)
                logger.info(f"Uploading {parties_path.name} to Internet Archive...")
                await self.uploader.upload_parquet(
                    parties_path,
                    tribunal,
                    partition_date,
                    parties_size_mb,
                    parties_rows,
                )
                if cleanup_files:
                    parties_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to export parties: {e}", exc_info=True)

        # 6. Record in database (continuing with main flow)
        await self._record_export_success(
            partition_date,
            tribunal,
            ia_url,
            file_path.name,
            row_count,
            file_size_mb,
        )

        # 7. Clean up local main file if requested
        if cleanup_files:
            file_path.unlink()
            logger.debug(f"Removed local file: {file_path}")

        return {
            "skipped": False,
            "row_count": row_count,
            "file_size_mb": file_size_mb,
            "ia_url": ia_url,
        }

    async def _already_exported(self, partition_date: str, tribunal: str) -> bool:
        """Check if partition already exported.

        Args:
            partition_date: Date in YYYY-MM-DD format
            tribunal: Tribunal code

        Returns:
            True if already exported successfully
        """
        query = """
            SELECT COUNT(*) as count
            FROM parquet_exports
            WHERE tribunal = ? AND partition_date = ? AND status = 'completed'
        """

        result = await asyncio.to_thread(
            self.db.raw_sql,
            query,
            [tribunal, partition_date],
        )

        count = result.fetchone()[0]
        return count > 0

    async def _record_export_pending(
        self,
        partition_date: str,
        tribunal: str,
    ) -> None:
        """Record export as pending in database.

        Args:
            partition_date: Date in YYYY-MM-DD format
            tribunal: Tribunal code
        """
        item_id = f"causaganha-{partition_date}-{tribunal}"
        ia_url = f"https://archive.org/details/{item_id}"
        filename = f"causaganha-{partition_date}-{tribunal}.parquet"

        query = """
            INSERT INTO parquet_exports (
                tribunal, partition_date, ia_item_id, ia_url,
                parquet_filename, row_count, file_size_mb,
                uploaded_at, status
            ) VALUES (?, ?, ?, ?, ?, 0, 0, CURRENT_TIMESTAMP, 'pending')
            ON CONFLICT (tribunal, partition_date) DO UPDATE
            SET status = 'pending'
        """

        await asyncio.to_thread(
            self.db.raw_sql,
            query,
            [tribunal, partition_date, item_id, ia_url, filename],
        )

    async def _record_export_success(
        self,
        partition_date: str,
        tribunal: str,
        ia_url: str,
        filename: str,
        row_count: int,
        file_size_mb: float,
    ) -> None:
        """Record successful export in database.

        Args:
            partition_date: Date in YYYY-MM-DD format
            tribunal: Tribunal code
            ia_url: Internet Archive URL
            filename: Parquet filename
            row_count: Number of rows exported
            file_size_mb: File size in MB
        """
        item_id = ia_url.split("/")[-1]

        query = """
            INSERT INTO parquet_exports (
                tribunal, partition_date, ia_item_id, ia_url,
                parquet_filename, row_count, file_size_mb,
                uploaded_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'completed')
            ON CONFLICT (tribunal, partition_date) DO UPDATE
            SET ia_item_id = excluded.ia_item_id,
                ia_url = excluded.ia_url,
                parquet_filename = excluded.parquet_filename,
                row_count = excluded.row_count,
                file_size_mb = excluded.file_size_mb,
                uploaded_at = CURRENT_TIMESTAMP,
                status = 'completed',
                error_message = NULL
        """

        await asyncio.to_thread(
            self.db.raw_sql,
            query,
            [
                tribunal,
                partition_date,
                item_id,
                ia_url,
                filename,
                row_count,
                file_size_mb,
            ],
        )

        logger.debug(f"Recorded successful export: {tribunal} {partition_date}")

    async def _record_export_failure(
        self,
        partition_date: str,
        tribunal: str,
        error: str,
    ) -> None:
        """Record failed export in database.

        Args:
            partition_date: Date in YYYY-MM-DD format
            tribunal: Tribunal code
            error: Error message
        """
        item_id = f"causaganha-{partition_date}-{tribunal}"
        ia_url = f"https://archive.org/details/{item_id}"
        filename = f"causaganha-{partition_date}-{tribunal}.parquet"

        query = """
            INSERT INTO parquet_exports (
                tribunal, partition_date, ia_item_id, ia_url,
                parquet_filename, row_count, file_size_mb,
                uploaded_at, status, error_message
            ) VALUES (?, ?, ?, ?, ?, 0, 0, CURRENT_TIMESTAMP, 'failed', ?)
            ON CONFLICT (tribunal, partition_date) DO UPDATE
            SET status = 'failed',
                error_message = excluded.error_message,
                uploaded_at = CURRENT_TIMESTAMP
        """

        await asyncio.to_thread(
            self.db.raw_sql,
            query,
            [tribunal, partition_date, item_id, ia_url, filename, error],
        )

        logger.debug(f"Recorded failed export: {tribunal} {partition_date}")

    async def _purge_old_data(self, current_date: str) -> None:
        """Purge intimations older than 6 months that have been exported.

        Args:
            current_date: Current date being processed (YYYY-MM-DD)
        """
        # Calculate cutoff date (6 months ago)
        current = datetime.strptime(current_date, "%Y-%m-%d").date()
        cutoff = current - timedelta(days=180)
        cutoff_str = cutoff.strftime("%Y-%m-%d")

        logger.info(f"Purging data older than {cutoff_str}")

        # Delete intimations that have been exported
        query = """
            DELETE FROM intimations
            WHERE data_disponibilizacao < ?
            AND data_disponibilizacao IN (
                SELECT DISTINCT partition_date
                FROM parquet_exports
                WHERE status = 'completed'
            )
        """

        result = await asyncio.to_thread(self.db.raw_sql, query, [cutoff_str])

        rows_deleted = result.rowcount if hasattr(result, "rowcount") else 0
        logger.info(f"Purged {rows_deleted:,} old intimation rows")

    async def backfill_historical(
        self,
        start_date: str,
        end_date: str,
        cleanup_files: bool = True,
    ) -> dict:
        """Backfill historical data exports.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            cleanup_files: Remove local files after upload

        Returns:
            Backfill summary with statistics
        """
        logger.info(f"Starting backfill from {start_date} to {end_date}")

        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        if start > end:
            raise ValueError("start_date must be before end_date")

        # Track overall results
        summary = {
            "start_date": start_date,
            "end_date": end_date,
            "total_days": (end - start).days + 1,
            "successful_days": 0,
            "failed_days": 0,
            "total_tribunals": 0,
            "successful_exports": 0,
            "failed_exports": 0,
        }

        # Process each date
        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")

            try:
                result = await self.run_daily_export(date_str, cleanup_files)

                summary["successful_days"] += 1
                summary["total_tribunals"] += result["total_tribunals"]
                summary["successful_exports"] += result["successful"]
                summary["failed_exports"] += result["failed"]

                logger.info(
                    f"Backfilled {date_str}: {result['successful']}/{result['total_tribunals']} successful",
                )

            except Exception as e:
                summary["failed_days"] += 1
                logger.error(f"Failed to backfill {date_str}: {e}")

            # Move to next day
            current += timedelta(days=1)

            # Small delay to avoid overwhelming IA
            await asyncio.sleep(1)

        logger.info(
            f"Backfill complete: {summary['successful_days']}/{summary['total_days']} days, "
            f"{summary['successful_exports']} exports",
        )

        return summary

    @staticmethod
    def _get_yesterday() -> str:
        """Get yesterday's date in YYYY-MM-DD format."""
        yesterday = date.today() - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d")
