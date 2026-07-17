"""Readiness gates (RFC 0012 §12.1, §14): rigid vs. advisory, a closed allowlist.

There is no generic ``--skip-gates`` (RFC 0012 §3.5, §12) — and per-gate
waivers alone are not enough either, because waiving every gate one by one
is the same antipattern with extra ceremony (§12.1). Every gate belongs to
exactly one of two fixed classes:

- **rigid** — never waivable, always blocks the release. Fixed by this
  module, not configurable by a caller: schema validity, unresolved
  annotation conflicts, split leakage, test contamination, checksum/build
  integrity, and the IAA floor (§8).
- **advisory** — a small, closed allowlist (tribunal diversity, source
  diversity, temporal diversity, representative eval set, external test
  review — exactly RFC 0012 §14's "exigidos para alegações amplas de
  produção"). A failing advisory gate blocks the release unless it has a
  matching :class:`~segmenter_dataset.schemas.KnownLimitation` entry.

A gate name outside both sets is a programming error, not a silently
permitted waiver — :func:`classify_gate` raises rather than defaulting.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from segmenter_dataset.schemas import KnownLimitation


class GateSeverity(StrEnum):
    """Which class a gate belongs to (RFC 0012 §12.1)."""

    RIGID = "rigid"
    ADVISORY = "advisory"


# RFC 0012 §14 "Exigidos para treino baseline" — all rigid (§12.1).
RIGID_GATES: frozenset[str] = frozenset(
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

# RFC 0012 §14 "Exigidos para alegações amplas de produção" — the only gates
# eligible for a known_limitation (§12.1). Closed: nothing outside this set
# may ever be waived.
ADVISORY_GATES: frozenset[str] = frozenset(
    {
        "multiple_tribunals",
        "multiple_source_systems",
        "temporal_diversity",
        "representative_evaluation_set",
        "external_test_annotation_review",
    }
)


class UnknownGateError(ValueError):
    """A gate name is neither rigid nor advisory — not silently permitted."""


def classify_gate(name: str) -> GateSeverity:
    """Return the fixed severity class of a gate; raises for an unknown name."""
    if name in RIGID_GATES:
        return GateSeverity.RIGID
    if name in ADVISORY_GATES:
        return GateSeverity.ADVISORY
    msg = (
        f"unknown gate {name!r} — not in RIGID_GATES or ADVISORY_GATES; "
        "adding a new gate requires updating RFC 0012 §12.1/§14, not a CLI flag"
    )
    raise UnknownGateError(msg)


@dataclass(frozen=True)
class GateResult:
    """Outcome of evaluating one gate."""

    name: str
    passed: bool
    detail: str = ""

    @property
    def severity(self) -> GateSeverity:
        """This gate's fixed class — rigid or advisory (RFC 0012 §12.1)."""
        return classify_gate(self.name)


@dataclass(frozen=True)
class GateEvaluation:
    """Aggregate outcome of every gate for a release attempt."""

    release_allowed: bool
    blocking_rigid_failures: tuple[GateResult, ...]
    blocking_unwaived_advisory_failures: tuple[GateResult, ...]
    waived_advisory_failures: tuple[GateResult, ...]


def evaluate_gates(
    results: list[GateResult], known_limitations: list[KnownLimitation]
) -> GateEvaluation:
    """Combine gate results with recorded known limitations (RFC 0012 §12.1).

    A rigid failure always blocks, regardless of ``known_limitations`` — no
    known-limitation entry can reference a rigid gate name (RFC 0012 §12.1
    closes that loophole by construction: only advisory gate names are ever
    checked against the ``known_limitations`` list here).
    """
    waived_gate_names = {kl.gate for kl in known_limitations}

    rigid_failures = tuple(r for r in results if not r.passed and r.severity is GateSeverity.RIGID)
    advisory_failures = tuple(
        r for r in results if not r.passed and r.severity is GateSeverity.ADVISORY
    )
    waived = tuple(r for r in advisory_failures if r.name in waived_gate_names)
    unwaived = tuple(r for r in advisory_failures if r.name not in waived_gate_names)

    return GateEvaluation(
        release_allowed=not rigid_failures and not unwaived,
        blocking_rigid_failures=rigid_failures,
        blocking_unwaived_advisory_failures=unwaived,
        waived_advisory_failures=waived,
    )
