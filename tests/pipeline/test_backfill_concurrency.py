import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock
import time
from causaganha.pipeline.export_orchestrator import ExportOrchestrator
from causaganha.pipeline.models import ExportResult, TribunalExportResult

@pytest.mark.asyncio
async def test_backfill_historical_concurrency():
    # Mocks
    repository = MagicMock()
    exporter = MagicMock()
    uploader = MagicMock()

    orchestrator = ExportOrchestrator(repository, exporter, uploader)

    # Mock run_daily_export to simulate work (sleep)
    async def mock_run_export(date, cleanup):
        await asyncio.sleep(0.1)
        # Create a result with 1 successful tribunal
        tribunal_result = TribunalExportResult(
            tribunal="TEST",
            success=True,
            row_count=100,
            file_size_mb=1.0
        )
        return ExportResult(
            partition_date=date,
            total_tribunals=1,
            tribunal_results=(tribunal_result,),
            duration_seconds=0.1
        )

    orchestrator.run_daily_export = AsyncMock(side_effect=mock_run_export)

    start_date = "2023-01-01"
    end_date = "2023-01-05" # 5 days

    start_time = time.time()
    summary = await orchestrator.backfill_historical(
        start_date,
        end_date,
        cleanup_files=True,
        concurrency=5
    )
    end_time = time.time()
    duration = end_time - start_time

    # Verification
    assert summary["successful_days"] == 5
    assert summary["total_days"] == 5
    assert orchestrator.run_daily_export.call_count == 5

    print(f"Duration: {duration:.4f}s")
    assert duration < 1.5 # Should be well under 3.0s

@pytest.mark.asyncio
async def test_backfill_historical_limited_concurrency():
    # Test that concurrency limit is respected (indirectly by timing)
    repository = MagicMock()
    exporter = MagicMock()
    uploader = MagicMock()

    orchestrator = ExportOrchestrator(repository, exporter, uploader)

    async def mock_run_export(date, cleanup):
        await asyncio.sleep(0.1)
        tribunal_result = TribunalExportResult(
            tribunal="TEST",
            success=True,
            row_count=100,
            file_size_mb=1.0
        )
        return ExportResult(
            partition_date=date,
            total_tribunals=1,
            tribunal_results=(tribunal_result,),
            duration_seconds=0.1
        )

    orchestrator.run_daily_export = AsyncMock(side_effect=mock_run_export)

    # 4 days, concurrency=2
    # Batch 1: Day 1, Day 2 (0.6s)
    # Batch 2: Day 3, Day 4 (0.6s)
    # Total ~1.2s

    start_time = time.time()
    await orchestrator.backfill_historical(
        "2023-01-01",
        "2023-01-04",
        concurrency=2
    )
    end_time = time.time()
    duration = end_time - start_time

    print(f"Duration (limited): {duration:.4f}s")
    # Should be slower than fully concurrent (0.6s) but faster than sequential (2.4s)
    assert duration > 0.6
    assert duration < 2.0

@pytest.mark.asyncio
async def test_backfill_historical_error_handling():
    repository = MagicMock()
    exporter = MagicMock()
    uploader = MagicMock()

    orchestrator = ExportOrchestrator(repository, exporter, uploader)

    # Make one date fail
    async def mock_run_export(date, cleanup):
        if date == "2023-01-02":
            raise ValueError("Simulation failure")
        tribunal_result = TribunalExportResult(
            tribunal="TEST",
            success=True,
            row_count=100,
            file_size_mb=1.0
        )
        return ExportResult(
            partition_date=date,
            total_tribunals=1,
            tribunal_results=(tribunal_result,),
            duration_seconds=0.1
        )

    orchestrator.run_daily_export = AsyncMock(side_effect=mock_run_export)

    summary = await orchestrator.backfill_historical(
        "2023-01-01",
        "2023-01-03",
        concurrency=3
    )

    assert summary["successful_days"] == 2
    assert summary["failed_days"] == 1
    assert summary["total_days"] == 3
