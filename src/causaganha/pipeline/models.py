"""Immutable data models for the export pipeline.

Follows the pattern from scripts/pipeline/run.py - pure data objects
with no side effects. All state is immutable (frozen dataclasses).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ExportPlan:
    """Pure: What needs to be exported (immutable plan)."""

    partition_date: str
    tribunals: tuple[str, ...]  # Immutable tuple
    cleanup_files: bool = True

    def validate(self) -> None:
        """Validate plan is executable.

        Raises:
            ValueError: If plan is invalid
        """
        if not self.tribunals:
            raise ValueError("ExportPlan: no tribunals to export")

        # Validate date format (YYYY-MM-DD)
        try:
            parts = self.partition_date.split("-")
            if len(parts) != 3:
                raise ValueError("Invalid date format")
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            if not (1000 <= year <= 9999 and 1 <= month <= 12 and 1 <= day <= 31):
                raise ValueError("Invalid date values")
        except (ValueError, AttributeError) as e:
            raise ValueError(f"ExportPlan: invalid date format '{self.partition_date}': {e}")


@dataclass(frozen=True)
class TribunalExportResult:
    """Result of exporting one tribunal (immutable)."""

    tribunal: str
    success: bool
    skipped: bool = False
    row_count: int = 0
    file_size_mb: float = 0.0
    ia_url: str = ""
    error: str = ""

    def validate(self) -> None:
        """Validate result consistency.

        Raises:
            ValueError: If result is inconsistent
        """
        if self.skipped and self.success:
            # Skipped exports are successful (no work needed)
            pass

        if not self.success and not self.error:
            raise ValueError("Failed exports must have an error message")

        if self.success and self.error:
            raise ValueError("Successful exports should not have an error message")

        if not self.success and (self.ia_url or self.row_count > 0):
            raise ValueError("Failed exports should not have upload URL or row count")


@dataclass(frozen=True)
class ExportResult:
    """Complete export pipeline result (immutable)."""

    partition_date: str
    total_tribunals: int
    tribunal_results: tuple[TribunalExportResult, ...] = field(default_factory=tuple)
    duration_seconds: float = 0.0

    @property
    def successful(self) -> int:
        """Count successful (non-skipped) exports."""
        return sum(
            1 for r in self.tribunal_results
            if r.success and not r.skipped
        )

    @property
    def failed(self) -> int:
        """Count failed exports."""
        return sum(1 for r in self.tribunal_results if not r.success)

    @property
    def skipped(self) -> int:
        """Count skipped exports."""
        return sum(1 for r in self.tribunal_results if r.skipped)

    @property
    def total_rows(self) -> int:
        """Total rows exported across all tribunals."""
        return sum(r.row_count for r in self.tribunal_results)

    @property
    def total_size_mb(self) -> float:
        """Total file size exported (MB)."""
        return sum(r.file_size_mb for r in self.tribunal_results)

    @property
    def failures(self) -> list[dict[str, str]]:
        """List of failures with tribunal and error."""
        return [
            {"tribunal": r.tribunal, "error": r.error}
            for r in self.tribunal_results
            if not r.success
        ]

    def to_dict(self) -> dict[str, int | str | float | list[dict[str, str]]]:  # type: ignore[return-value]
        """Convert to dictionary for JSON serialization."""
        return {
            "date": self.partition_date,
            "total_tribunals": self.total_tribunals,
            "successful": self.successful,
            "failed": self.failed,
            "skipped": self.skipped,
            "total_rows": self.total_rows,
            "total_size_mb": self.total_size_mb,
            "failures": self.failures,
            "duration_seconds": self.duration_seconds,
        }

    def validate(self) -> None:
        """Validate result consistency.

        Raises:
            ValueError: If result is inconsistent
        """
        if len(self.tribunal_results) != self.total_tribunals:
            raise ValueError(
                f"ExportResult: total_tribunals ({self.total_tribunals}) "
                f"does not match tribunal_results length ({len(self.tribunal_results)})"
            )

        if self.duration_seconds < 0:
            raise ValueError("ExportResult: duration_seconds cannot be negative")

        # Validate each tribunal result
        for r in self.tribunal_results:
            r.validate()
