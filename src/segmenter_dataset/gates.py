"""Readiness gates: rigid invariants and a closed advisory allowlist."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from segmenter_dataset.schemas import KnownLimitation


class GateSeverity(StrEnum):
    """Whether a gate is non-waivable or an advisory limitation."""

    RIGID = "rigid"
    ADVISORY = "advisory"


RIGID_GATES = frozenset(
    {
        "ontology_schema_valid",
        "split_disjoint_by_group_id_hash",
        "no_unresolved_annotation_conflicts",
        "val_test_independently_adjudicated",
        "iaa_aggregate_floor",
        "iaa_critical_category_floor",
        "train_minimum_support_per_category",
        "val_minimum_support_for_reported_metrics",
        "release_checksums_generated",
        "ci_reproducible_build",
    }
)
ADVISORY_GATES = frozenset(
    {
        "multiple_tribunals",
        "multiple_source_systems",
        "temporal_diversity",
        "representative_evaluation_set",
        "external_test_annotation_review",
    }
)


class UnknownGateError(ValueError):
    """A gate name is outside the RFC's closed classification."""


class InvalidKnownLimitationError(ValueError):
    """A known limitation attempts to waive a rigid or unknown gate."""


def classify_gate(name: str) -> GateSeverity:
    """Return the fixed RFC severity for a gate name."""
    if name in RIGID_GATES:
        return GateSeverity.RIGID
    if name in ADVISORY_GATES:
        return GateSeverity.ADVISORY
    message = f"unknown gate {name!r}; adding a gate requires updating RFC 0012"
    raise UnknownGateError(message)


@dataclass(frozen=True)
class GateResult:
    """One gate's pass/fail result and human-readable evidence."""

    name: str
    passed: bool
    detail: str = ""

    @property
    def severity(self) -> GateSeverity:
        """Return this gate's fixed RFC severity."""
        return classify_gate(self.name)


@dataclass(frozen=True)
class GateEvaluation:
    """Combined outcome after applying advisory known limitations."""

    release_allowed: bool
    blocking_rigid_failures: tuple[GateResult, ...]
    blocking_unwaived_advisory_failures: tuple[GateResult, ...]
    waived_advisory_failures: tuple[GateResult, ...]


def evaluate_gates(
    results: list[GateResult], known_limitations: list[KnownLimitation]
) -> GateEvaluation:
    """Evaluate gates after rejecting invalid waiver declarations."""
    for limitation in known_limitations:
        try:
            severity = classify_gate(limitation.gate)
        except UnknownGateError as exc:
            raise InvalidKnownLimitationError(str(exc)) from exc
        if severity is GateSeverity.RIGID:
            message = f"known limitation cannot reference rigid gate {limitation.gate!r}"
            raise InvalidKnownLimitationError(message)
        if limitation.status != "known_limitation" or not limitation.reason.strip():
            message = f"invalid known limitation for gate {limitation.gate!r}"
            raise InvalidKnownLimitationError(message)

    waived_gate_names = {limitation.gate for limitation in known_limitations}
    rigid_failures = tuple(
        result for result in results if not result.passed and result.severity is GateSeverity.RIGID
    )
    advisory_failures = tuple(
        result
        for result in results
        if not result.passed and result.severity is GateSeverity.ADVISORY
    )
    waived = tuple(result for result in advisory_failures if result.name in waived_gate_names)
    unwaived = tuple(result for result in advisory_failures if result.name not in waived_gate_names)
    return GateEvaluation(
        release_allowed=not rigid_failures and not unwaived,
        blocking_rigid_failures=rigid_failures,
        blocking_unwaived_advisory_failures=unwaived,
        waived_advisory_failures=waived,
    )
