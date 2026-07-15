"""Tests for scripts.synthetic_segmenter.split_guard — RFC 0011 §10 invariants."""

from __future__ import annotations

import pytest

from scripts.synthetic_segmenter.split_guard import (
    SplitAssignment,
    SplitLeakError,
    assign_child_split,
    calibration_eligible_ids,
    check_disjoint,
    require_train_only_sources,
)


def _assignment() -> SplitAssignment:
    return SplitAssignment(
        train_ids=frozenset({"doc_1", "doc_2", "doc_3"}),
        val_ids=frozenset({"doc_4"}),
        test_ids=frozenset({"doc_5"}),
    )


def test_disjoint_splits_construct_cleanly() -> None:
    assignment = _assignment()
    assert assignment.split_of("doc_1") == "train"
    assert assignment.split_of("doc_4") == "val"
    assert assignment.split_of("doc_5") == "test"
    assert assignment.split_of("doc_unknown") is None


def test_overlapping_splits_raise_on_construction() -> None:
    with pytest.raises(SplitLeakError):
        SplitAssignment(
            train_ids=frozenset({"doc_1"}),
            val_ids=frozenset({"doc_1"}),
            test_ids=frozenset(),
        )


def test_check_disjoint_reports_all_violations() -> None:
    violations = check_disjoint(frozenset({"a", "b"}), frozenset({"b", "c"}), frozenset({"c", "a"}))
    assert len(violations) == 3


def test_check_disjoint_clean_returns_empty() -> None:
    assert check_disjoint(frozenset({"a"}), frozenset({"b"}), frozenset({"c"})) == []


def test_augmented_child_inherits_parent_split() -> None:
    assignment = _assignment()
    assert assign_child_split("doc_1", assignment) == "train"
    assert assign_child_split("doc_4", assignment) == "val"


def test_augmented_child_of_unknown_parent_raises() -> None:
    assignment = _assignment()
    with pytest.raises(SplitLeakError, match="not in any known split"):
        assign_child_split("doc_ghost", assignment)


def test_require_train_only_sources_accepts_train_docs() -> None:
    assignment = _assignment()
    require_train_only_sources(["doc_1", "doc_2"], assignment)  # no raise


def test_require_train_only_sources_rejects_val_test_and_unknown() -> None:
    assignment = _assignment()
    with pytest.raises(SplitLeakError) as exc_info:
        require_train_only_sources(["doc_1", "doc_4", "doc_5", "doc_ghost"], assignment)
    msg = str(exc_info.value)
    assert "doc_4" in msg
    assert "doc_5" in msg
    assert "doc_ghost" in msg
    assert "doc_1" not in msg


def test_calibration_eligible_ids_excludes_val_test_and_unassigned() -> None:
    assignment = _assignment()
    all_ids = frozenset({"doc_1", "doc_2", "doc_4", "doc_5", "doc_unassigned"})
    eligible = calibration_eligible_ids(all_ids, assignment)
    assert eligible == frozenset({"doc_1", "doc_2"})


def test_calibration_eligible_ids_never_includes_unassigned_docs() -> None:
    """RFC 0011 §6.1 hardening: a doc that MIGHT become val/test later must
    not calibrate anything before it's actually assigned — not even if it's
    the only doc in ``all_known_ids`` that isn't in val/test explicitly.
    """
    assignment = _assignment()
    all_ids = frozenset({"brand_new_doc_not_yet_split"})
    assert calibration_eligible_ids(all_ids, assignment) == frozenset()
