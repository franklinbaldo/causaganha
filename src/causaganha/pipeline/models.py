from __future__ import annotations


MAX_DAY_OF_MONTH = 31
MAX_MONTH = 12
MAX_YEAR = 9999
MIN_YEAR = 1000
DATE_PARTS_COUNT = 3

"""Immutable data models for the export pipeline.

Follows the pattern from scripts/pipeline/run.py - pure data objects
with no side effects. All state is immutable (frozen dataclasses).
"""


from dataclasses import dataclass, field


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
            msg = "ExportPlan: no tribunals to export"
            raise ValueError(msg)

        # Validate date format (YYYY-MM-DD)
        try:
            parts = self.partition_date.split("-")
            if len(parts) != DATE_PARTS_COUNT:
                msg = "Invalid date format"
                raise ValueError(msg)  # noqa: TRY301
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            if not (
                MIN_YEAR <= year <= MAX_YEAR
                and 1 <= month <= MAX_MONTH
                and 1 <= day <= DATE_PARTS_COUNT1
            ):
                msg = "Invalid date values"
                raise ValueError(msg)  # noqa: TRY301
        except (ValueError, AttributeError) as e:
            msg = f"ExportPlan: invalid date format '{self.partition_date}': {e}"
            raise ValueError(msg) from e


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
            msg = "Failed exports must have an error message"
            raise ValueError(msg)

        if self.success and self.error:
            msg = "Successful exports should not have an error message"
            raise ValueError(msg)

        if not self.success and (self.ia_url or self.row_count > 0):
            msg = "Failed exports should not have upload URL or row count"
            raise ValueError(msg)


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
        return sum(1 for r in self.tribunal_results if r.success and not r.skipped)

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
            msg = (
                f"ExportResult: total_tribunals ({self.total_tribunals}) "
                f"does not match tribunal_results length ({len(self.tribunal_results)})"
            )
            raise ValueError(
                msg,
            )

        if self.duration_seconds < 0:
            msg = "ExportResult: duration_seconds cannot be negative"
            raise ValueError(msg)

        # Validate each tribunal result
        for r in self.tribunal_results:
            r.validate()
