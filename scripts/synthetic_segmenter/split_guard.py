"""Source-family split enforcement (RFC 0011 §10 — non-negotiable invariants).

Order of operations this module assumes and enforces:

1. pristine real documents are split into train/val/test FIRST, before any
   generation or augmentation touches them;
2. augmentation only happens after that split, and the augmented record
   inherits its parent's split;
3. real excerpts in hybrid/synthetic records may only come from TRAIN
   documents;
4. no text from val/test documents reaches training data by any path;
5. corpus-wide statistics (RFC 0011 §6.1) may use train documents, but must
   exclude val/test hashes even for aggregate calibration — including
   documents not yet assigned to any split, which are simply not usable
   for calibration until they are (RFC 0011 §6.1 hardening: "documentos
   ainda não atribuídos a um split não calibram nada").
"""

from __future__ import annotations

from dataclasses import dataclass


class SplitLeakError(ValueError):
    """A source-family split invariant was violated."""


@dataclass(frozen=True)
class SplitAssignment:
    """Which split each pristine real source document belongs to."""

    train_ids: frozenset[str]
    val_ids: frozenset[str]
    test_ids: frozenset[str]

    def __post_init__(self) -> None:
        """Raise SplitLeakError immediately if the three sets aren't disjoint."""
        violations = check_disjoint(self.train_ids, self.val_ids, self.test_ids)
        if violations:
            raise SplitLeakError("; ".join(violations))

    def split_of(self, doc_id: str) -> str | None:
        """Return "train"/"val"/"test" for a known doc_id, else None."""
        if doc_id in self.train_ids:
            return "train"
        if doc_id in self.val_ids:
            return "val"
        if doc_id in self.test_ids:
            return "test"
        return None


def check_disjoint(
    train_ids: frozenset[str], val_ids: frozenset[str], test_ids: frozenset[str]
) -> list[str]:
    """Return violation messages for any pairwise intersection; empty = OK.

    RFC 0011 §10 validator:
        train_source_doc_ids & val_source_doc_ids == set()
        train_source_doc_ids & test_source_doc_ids == set()
        val_source_doc_ids & test_source_doc_ids == set()
    """
    violations: list[str] = []
    for name_a, ids_a, name_b, ids_b in (
        ("train", train_ids, "val", val_ids),
        ("train", train_ids, "test", test_ids),
        ("val", val_ids, "test", test_ids),
    ):
        overlap = ids_a & ids_b
        if overlap:
            violations.append(f"{name_a}/{name_b} overlap: {sorted(overlap)}")
    return violations


def assign_child_split(parent_doc_id: str, assignment: SplitAssignment) -> str:
    """Split an augmented/hybrid record inherits from its (pristine real) parent.

    Raises if the parent isn't a known pristine real document — an
    augmented/hybrid record with no traceable real parent is a provenance
    bug, not a case to silently default anywhere.
    """
    split = assignment.split_of(parent_doc_id)
    if split is None:
        msg = f"source_doc_id {parent_doc_id!r} is not in any known split — cannot inherit"
        raise SplitLeakError(msg)
    return split


def require_train_only_sources(source_doc_ids: list[str], assignment: SplitAssignment) -> None:
    """Enforce RFC 0011 §10.4.

    Real excerpts in hybrid/synthetic records come only from TRAIN
    documents. Raises SplitLeakError listing any offender.
    """
    offenders = [doc_id for doc_id in source_doc_ids if assignment.split_of(doc_id) != "train"]
    if offenders:
        msg = (
            f"source_doc_ids not in train split (val/test/unknown): {sorted(offenders)} "
            "— hybrid/synthetic records may only excerpt training documents (RFC 0011 §6.2)"
        )
        raise SplitLeakError(msg)


def calibration_eligible_ids(
    all_known_ids: frozenset[str], assignment: SplitAssignment
) -> frozenset[str]:
    """Documents ``corpus_stats.py`` may use for aggregate calibration (RFC 0011 §6.1).

    Train documents only. Documents not present in ``assignment`` at all
    (not yet split) are excluded too, by construction — they're simply not
    in ``assignment.train_ids``, so they never appear in the result. This
    is the fix for the earlier malformed rule: no "documents not yet
    assigned" carve-out exists; unassigned means unusable, full stop.
    """
    return frozenset(doc_id for doc_id in all_known_ids if assignment.split_of(doc_id) == "train")
