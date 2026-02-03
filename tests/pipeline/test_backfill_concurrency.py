"""Tests for backfill concurrency in ExportOrchestrator."""

import asyncio
from unittest.mock import MagicMock

import pytest

from causaganha.pipeline.export_orchestrator import ExportOrchestrator
from causaganha.pipeline.models import ExportResult, TribunalExportResult
from causaganha.pipeline.repositories import MockExportRepository


@pytest.mark.asyncio
async def test_backfill_historical_concurrency():
    """Test that backfill_historical respects concurrency."""
    repo = MockExportRepository()
    exporter = MagicMock()
    uploader = MagicMock()

    orchestrator = ExportOrchestrator(repo, exporter, uploader)

    # Mock run_daily_export to take some time
    active_tasks = 0
    max_active_tasks = 0

    async def delayed_export(date, cleanup):
        nonlocal active_tasks, max_active_tasks
        active_tasks += 1
        max_active_tasks = max(max_active_tasks, active_tasks)
        await asyncio.sleep(0.05)
        active_tasks -= 1
        return ExportResult(
            partition_date=date,
            total_tribunals=1,
            tribunal_results=(TribunalExportResult("TJSP", success=True),),
            duration_seconds=1.0,
        )

    # We need to patch the method on the instance
    orchestrator.run_daily_export = delayed_export

    # Run backfill with concurrency=3
    # 5 days: 2023-01-01 to 2023-01-05
    start_date = "2023-01-01"
    end_date = "2023-01-05"
    concurrency = 3

    await orchestrator.backfill_historical(
        start_date,
        end_date,
        concurrency=concurrency,
    )

    # Check if we achieved concurrency
    assert max_active_tasks <= concurrency
    assert max_active_tasks > 1, "Should have run at least 2 tasks concurrently"
