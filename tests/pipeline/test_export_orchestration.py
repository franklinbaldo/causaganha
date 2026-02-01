"""Tests for export orchestration - pure logic and repositories.

These tests demonstrate the key benefit of the refactored architecture:
- Pure orchestration logic is fully testable without DB or mocks
- Repositories can be tested in isolation
- MockExportRepository enables complete scenario testing
"""

import pytest

from causaganha.pipeline.models import (
    ExportPlan,
    ExportResult,
    TribunalExportResult,
)
from causaganha.pipeline.orchestration import PureOrchestrator
from causaganha.pipeline.repositories import MockExportRepository


# ── Tests for Immutable Models ──


class TestExportPlan:
    """Test ExportPlan validation and properties."""

    def test_plan_valid(self):
        """Valid plan creation."""
        plan = ExportPlan(
            partition_date="2026-01-15",
            tribunals=("TJSP", "TJRJ"),
        )
        assert plan.partition_date == "2026-01-15"
        assert len(plan.tribunals) == 2
        assert plan.cleanup_files is True

    def test_plan_immutable(self):
        """Plan is frozen (immutable)."""
        plan = ExportPlan(
            partition_date="2026-01-15",
            tribunals=("TJSP",),
        )
        with pytest.raises(AttributeError):
            plan.tribunals = ("TJRJ",)

    def test_plan_invalid_date_format(self):
        """Invalid date format raises error on validate()."""
        plan = ExportPlan(
            partition_date="01-15-2026",  # Wrong format
            tribunals=("TJSP",),
        )
        with pytest.raises(ValueError, match="invalid date format"):
            plan.validate()

    def test_plan_empty_tribunals(self):
        """Empty tribunal list raises error on validate()."""
        plan = ExportPlan(
            partition_date="2026-01-15",
            tribunals=(),
        )
        with pytest.raises(ValueError, match="no tribunals"):
            plan.validate()


class TestTribunalExportResult:
    """Test TribunalExportResult validation."""

    def test_result_success_without_error(self):
        """Successful export has no error message."""
        result = TribunalExportResult(
            tribunal="TJSP",
            success=True,
            row_count=100,
            file_size_mb=5.0,
            ia_url="https://archive.org/details/djen-raw-2026-01-15-TJSP",
        )
        assert result.success
        assert result.error == ""

    def test_result_skipped(self):
        """Skipped exports are successful with no data."""
        result = TribunalExportResult(
            tribunal="TJSP",
            success=True,
            skipped=True,
        )
        assert result.success
        assert result.skipped

    def test_result_failure_requires_error(self):
        """Failed export requires error message on validate()."""
        result = TribunalExportResult(
            tribunal="TJSP",
            success=False,
        )
        with pytest.raises(ValueError, match="must have an error"):
            result.validate()

    def test_result_failure_has_error(self):
        """Failed export with error message."""
        result = TribunalExportResult(
            tribunal="TJSP",
            success=False,
            error="Connection timeout",
        )
        assert not result.success
        assert result.error == "Connection timeout"


class TestExportResult:
    """Test ExportResult aggregation and properties."""

    def test_result_aggregates_stats(self):
        """Result correctly aggregates tribunal statistics."""
        r1 = TribunalExportResult("TJSP", success=True, row_count=100, file_size_mb=5.0)
        r2 = TribunalExportResult("TJRJ", success=True, row_count=200, file_size_mb=10.0)
        r3 = TribunalExportResult("TJMG", success=False, error="Failed")

        result = ExportResult(
            partition_date="2026-01-15",
            total_tribunals=3,
            tribunal_results=(r1, r2, r3),
            duration_seconds=60.0,
        )

        assert result.successful == 2
        assert result.failed == 1
        assert result.skipped == 0
        assert result.total_rows == 300
        assert result.total_size_mb == 15.0

    def test_result_failures_list(self):
        """Result extracts failure information."""
        r1 = TribunalExportResult("TJSP", success=False, error="Timeout")
        r2 = TribunalExportResult("TJRJ", success=True)

        result = ExportResult(
            partition_date="2026-01-15",
            total_tribunals=2,
            tribunal_results=(r1, r2),
            duration_seconds=30.0,
        )

        assert len(result.failures) == 1
        assert result.failures[0]["tribunal"] == "TJSP"
        assert result.failures[0]["error"] == "Timeout"

    def test_result_to_dict(self):
        """Result can be serialized to dict for JSON."""
        r1 = TribunalExportResult("TJSP", success=True, row_count=100, file_size_mb=5.0)
        result = ExportResult(
            partition_date="2026-01-15",
            total_tribunals=1,
            tribunal_results=(r1,),
            duration_seconds=30.0,
        )

        d = result.to_dict()
        assert d["date"] == "2026-01-15"
        assert d["successful"] == 1
        assert d["total_rows"] == 100
        assert d["duration_seconds"] == 30.0


# ── Tests for Pure Orchestration Logic ──


class TestPureOrchestrator:
    """Test pure orchestration logic (no I/O, fully deterministic)."""

    def test_plan_export_creates_valid_plan(self):
        """plan_export builds and validates a plan."""
        plan = PureOrchestrator.plan_export(
            "2026-01-15",
            ("TJSP", "TJRJ", "TJMG"),
            cleanup_files=True,
        )

        assert plan.partition_date == "2026-01-15"
        assert len(plan.tribunals) == 3
        assert plan.cleanup_files is True

    def test_plan_export_invalid_date_raises(self):
        """plan_export validates date format."""
        with pytest.raises(ValueError, match="invalid date format"):
            PureOrchestrator.plan_export(
                "invalid-date",
                ("TJSP",),
            )

    def test_add_tribunal_result_immutability(self):
        """add_tribunal_result doesn't mutate input."""
        original = ()
        r1 = TribunalExportResult("TJSP", success=True)
        r2 = TribunalExportResult("TJRJ", success=True)

        result1 = PureOrchestrator.add_tribunal_result(original, r1)
        result2 = PureOrchestrator.add_tribunal_result(result1, r2)

        # Original unchanged
        assert len(original) == 0
        assert len(result1) == 1
        assert len(result2) == 2

    def test_aggregate_results_validates_length(self):
        """aggregate_results validates tribunal count on validate()."""
        r1 = TribunalExportResult("TJSP", success=True)

        result = ExportResult(
            partition_date="2026-01-15",
            total_tribunals=2,  # Says 2 but only 1 provided
            tribunal_results=(r1,),
            duration_seconds=30.0,
        )
        with pytest.raises(ValueError, match="does not match"):
            result.validate()

    def test_should_purge_data_checks_success(self):
        """should_purge_data returns True only if exports succeeded."""
        result_success = ExportResult(
            partition_date="2026-01-15",
            total_tribunals=1,
            tribunal_results=(TribunalExportResult("TJSP", success=True),),
            duration_seconds=30.0,
        )
        assert PureOrchestrator.should_purge_data(result_success) is True

        result_fail = ExportResult(
            partition_date="2026-01-15",
            total_tribunals=1,
            tribunal_results=(TribunalExportResult("TJSP", success=False, error="Failed"),),
            duration_seconds=30.0,
        )
        assert PureOrchestrator.should_purge_data(result_fail) is False

    def test_get_yesterday_date_format(self):
        """get_yesterday_date returns valid YYYY-MM-DD string."""
        yesterday = PureOrchestrator.get_yesterday_date()
        parts = yesterday.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4  # YYYY
        assert len(parts[1]) == 2  # MM
        assert len(parts[2]) == 2  # DD


# ── Tests for Mock Repository ──


class TestMockExportRepository:
    """Test MockExportRepository for scenario testing."""

    @pytest.mark.asyncio
    async def test_mock_repository_workflows(self):
        """Test complete workflow with mock repository."""
        repo = MockExportRepository(tribunals=("TJSP", "TJRJ"))

        # Get tribunals
        tribunals = await repo.get_tribunals_for_date("2026-01-15")
        assert len(tribunals) == 2

        # Record pending
        await repo.record_pending("2026-01-15", "TJSP")
        assert ("2026-01-15", "TJSP") in repo.pending

        # Check not yet exported
        is_exported = await repo.is_already_exported("2026-01-15", "TJSP")
        assert is_exported is False

        # Record success
        await repo.record_success(
            "2026-01-15",
            "TJSP",
            ia_url="https://archive.org/details/djen-raw-2026-01-15-TJSP",
            filename="TJSP-2026-01-15-comunicacoes.parquet",
            row_count=100,
            size_mb=5.0,
        )

        # Check now exported
        is_exported = await repo.is_already_exported("2026-01-15", "TJSP")
        assert is_exported is True

        # Record failure for different tribunal
        await repo.record_failure(
            "2026-01-15",
            "TJRJ",
            error="Connection timeout",
        )

        assert ("2026-01-15", "TJRJ") in repo.failures

    @pytest.mark.asyncio
    async def test_mock_repository_purge_is_noop(self):
        """Mock repository purge does nothing (for testing)."""
        repo = MockExportRepository()
        # Should not raise
        await repo.purge_old_data("2026-01-15")


# ── Integration Tests (Using Mock Repository) ──


class TestOrchestrationScenarios:
    """Test orchestration scenarios using mock repository."""

    def test_scenario_all_success(self):
        """Scenario: All tribunals export successfully."""
        r1 = TribunalExportResult("TJSP", success=True, row_count=100, file_size_mb=5.0)
        r2 = TribunalExportResult("TJRJ", success=True, row_count=200, file_size_mb=10.0)

        result = ExportResult(
            partition_date="2026-01-15",
            total_tribunals=2,
            tribunal_results=(r1, r2),
            duration_seconds=45.0,
        )

        assert result.successful == 2
        assert result.failed == 0
        assert result.total_rows == 300
        # Purge should happen
        assert PureOrchestrator.should_purge_data(result)

    def test_scenario_partial_success(self):
        """Scenario: Some tribunals succeed, some fail."""
        r1 = TribunalExportResult("TJSP", success=True, row_count=100, file_size_mb=5.0)
        r2 = TribunalExportResult("TJRJ", success=False, error="Timeout")
        r3 = TribunalExportResult("TJMG", success=True, row_count=50, file_size_mb=2.5)

        result = ExportResult(
            partition_date="2026-01-15",
            total_tribunals=3,
            tribunal_results=(r1, r2, r3),
            duration_seconds=60.0,
        )

        assert result.successful == 2
        assert result.failed == 1
        assert result.total_rows == 150
        assert len(result.failures) == 1
        # Purge still happens (had some success)
        assert PureOrchestrator.should_purge_data(result)

    def test_scenario_with_skipped(self):
        """Scenario: Some skipped, some successful."""
        r1 = TribunalExportResult("TJSP", success=True, skipped=True)
        r2 = TribunalExportResult("TJRJ", success=True, row_count=200, file_size_mb=10.0)

        result = ExportResult(
            partition_date="2026-01-15",
            total_tribunals=2,
            tribunal_results=(r1, r2),
            duration_seconds=30.0,
        )

        assert result.successful == 1  # Only non-skipped
        assert result.skipped == 1
        assert result.total_rows == 200  # Skipped doesn't count
