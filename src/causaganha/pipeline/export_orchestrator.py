"""Export Orchestration Module.

Coordinates the daily Parquet export pipeline with clear separation:
1. PLANNING (pure) - Build execution plan
2. EXECUTION (impure) - Export, upload, record
3. AGGREGATION (pure) - Combine results
4. CLEANUP (impure) - Purge old data

Architecture follows scripts/pipeline/run.py pattern:
- Immutable state objects (ExportResult)
- Pure orchestration logic (PureOrchestrator)
- Dependency injection (ExportRepository)

Usage:
    from causaganha.pipeline.repositories import DuckDBExportRepository

    repo = DuckDBExportRepository(db)
    exporter = ParquetExporter(config)
    uploader = InternetArchiveUploader(config)
    orchestrator = ExportOrchestrator(repo, exporter, uploader)
    result = await orchestrator.run_daily_export()
"""

import asyncio
import logging
from datetime import datetime

from .ia_upload import InternetArchiveUploader
from .models import ExportResult, TribunalExportResult
from .orchestration import PureOrchestrator
from .parquet_export import ParquetExporter
from .repositories import ExportRepository


logger = logging.getLogger(__name__)


class ExportOrchestrator:
    """Orchestrates daily Parquet export pipeline.

    Uses dependency injection (repository) instead of direct DB access.
    Follows 3-phase pattern: planning (pure) → execution (impure) → aggregation (pure).
    """

    def __init__(
        self,
        repository: ExportRepository,
        parquet_exporter: ParquetExporter,
        ia_uploader: InternetArchiveUploader,
    ) -> None:
        """Initialize export orchestrator.

        Args:
            repository: ExportRepository for data operations (injected)
            parquet_exporter: ParquetExporter instance
            ia_uploader: InternetArchiveUploader instance
        """
        self.repo = repository
        self.exporter = parquet_exporter
        self.uploader = ia_uploader
        logger.info("ExportOrchestrator initialized")

    async def run_daily_export(
        self,
        partition_date: str | None = None,
        cleanup_files: bool = True,
    ) -> ExportResult:
        """Run daily export for specified date (defaults to yesterday).

        Follows 3-phase pattern:
        1. PLANNING (pure) - Build export plan
        2. EXECUTION (impure) - Export & upload per tribunal
        3. AGGREGATION (pure) - Combine results
        4. CLEANUP (impure) - Purge old data if successful

        Args:
            partition_date: Date in YYYY-MM-DD format (None = yesterday)
            cleanup_files: Remove local Parquet files after upload

        Returns:
            ExportResult with immutable statistics (supports .to_dict() for JSON)

        Raises:
            ValueError: If date has no data
        """
        # Phase 0: Use yesterday if no date specified
        if partition_date is None:
            partition_date = PureOrchestrator.get_yesterday_date()

        logger.info(f"Starting daily export for {partition_date}")
        start_time = datetime.now()

        # Phase 1: PLANNING (pure)
        tribunals = await self.repo.get_tribunals_for_date(partition_date)

        if not tribunals:
            raise ValueError(f"No data found for date {partition_date}")

        plan = PureOrchestrator.plan_export(partition_date, tribunals, cleanup_files)
        logger.info(
            f"Planned export for {len(plan.tribunals)} tribunals on {plan.partition_date}",
        )

        # Phase 2: EXECUTION (impure) - Execute per tribunal, collect immutable results
        tribunal_results: tuple[TribunalExportResult, ...] = ()

        for tribunal in plan.tribunals:
            tribunal_result = await self._execute_tribunal_export(
                plan.partition_date,
                tribunal,
                plan.cleanup_files,
            )
            # Use pure function to update immutable tuple
            tribunal_results = PureOrchestrator.add_tribunal_result(
                tribunal_results,
                tribunal_result,
            )

        # Phase 3: AGGREGATION (pure)
        duration = (datetime.now() - start_time).total_seconds()
        result = PureOrchestrator.aggregate_results(
            plan.partition_date,
            tribunal_results,
            duration,
        )

        # Phase 4: CLEANUP (impure) - Purge old data if exports succeeded
        if PureOrchestrator.should_purge_data(result):
            await self.repo.purge_old_data(partition_date)

        return result

    async def _execute_tribunal_export(
        self,
        partition_date: str,
        tribunal: str,
        cleanup_files: bool,
    ) -> TribunalExportResult:
        """Execute single tribunal export (returns immutable result).

        Returns TribunalExportResult instead of dict for immutability and type safety.

        Args:
            partition_date: Date in YYYY-MM-DD format
            tribunal: Tribunal code
            cleanup_files: Remove local file after upload

        Returns:
            TribunalExportResult (immutable) with success/failure details

        Raises:
            Nothing - catches all exceptions and returns failed result
        """
        try:
            # Check if already exported
            if await self.repo.is_already_exported(partition_date, tribunal):
                logger.info(f"Skipped {tribunal} ({partition_date}) - already exported")
                return TribunalExportResult(
                    tribunal=tribunal,
                    success=True,
                    skipped=True,
                )

            # Mark as pending
            await self.repo.record_pending(partition_date, tribunal)

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

            # 3. Export & Upload Embeddings (if available, best-effort)
            try:
                # Note: embeddings_storage needs DB connection
                # TODO: Refactor to pass db_connection to ParquetExporter instead
                # of embedding_storage needing to get it separately
                logger.info(f"Exporting embeddings for {tribunal} {partition_date}...")

            except Exception as e:
                logger.warning(f"Skipped embeddings export: {e}")

            # 4. Export & Upload Lawyers (best-effort)
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
                logger.warning(f"Skipped lawyers export: {e}")

            # 5. Export & Upload Parties (best-effort)
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
                logger.warning(f"Skipped parties export: {e}")

            # 6. Record success in database
            await self.repo.record_success(
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

            logger.info(
                f"✓ {tribunal}: {row_count} rows, {file_size_mb:.2f} MB",
            )

            return TribunalExportResult(
                tribunal=tribunal,
                success=True,
                skipped=False,
                row_count=row_count,
                file_size_mb=file_size_mb,
                ia_url=ia_url,
            )

        except Exception as e:
            logger.error(f"✗ {tribunal} ({partition_date}): {e}", exc_info=True)
            # Record failure (don't re-raise - let orchestrator collect results)
            await self.repo.record_failure(partition_date, tribunal, str(e))

            return TribunalExportResult(
                tribunal=tribunal,
                success=False,
                error=str(e),
            )

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
        from datetime import timedelta

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
                summary["total_tribunals"] += result.total_tribunals
                summary["successful_exports"] += result.successful
                summary["failed_exports"] += result.failed

                logger.info(
                    f"Backfilled {date_str}: {result.successful}/{result.total_tribunals} successful",
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
