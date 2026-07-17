from __future__ import annotations

import pytest
from conftest import make_annotation, make_document, make_review

from segmenter_dataset.splits import (
    GroupingKeys,
    SplitAssignment,
    SplitLeakError,
    assign_splits,
    build_groups,
    check_disjoint,
    evaluation_eligible_document_ids,
    train_eligible_document_ids,
    validate_split_leakage,
)


def test_check_disjoint_no_overlap() -> None:
    assert check_disjoint(frozenset({"a"}), frozenset({"b"}), frozenset({"c"})) == []


def test_check_disjoint_reports_overlap() -> None:
    violations = check_disjoint(frozenset({"a", "b"}), frozenset({"b"}), frozenset())
    assert any("train/val overlap" in v for v in violations)


def test_split_assignment_raises_on_overlap() -> None:
    with pytest.raises(SplitLeakError):
        SplitAssignment(frozenset({"a"}), frozenset({"a"}), frozenset())


def test_split_of() -> None:
    assignment = SplitAssignment(frozenset({"a"}), frozenset({"b"}), frozenset({"c"}))
    assert assignment.split_of("a") == "train"
    assert assignment.split_of("b") == "val"
    assert assignment.split_of("c") == "test"
    assert assignment.split_of("z") is None


def test_train_eligible_document_ids_needs_only_annotation() -> None:
    document = make_document()
    annotation = make_annotation(document)
    assert document.document_id in train_eligible_document_ids([annotation])


def test_evaluation_eligible_document_ids_needs_accepted_review() -> None:
    document = make_document()
    a = make_annotation(document, annotator_id="a", model_family="fam-a")
    b = make_annotation(document, annotator_id="b", model_family="fam-b")
    review = make_review(document, [a, b], status="accepted")
    assert document.document_id in evaluation_eligible_document_ids([review])


def test_build_groups_clusters_exact_duplicates() -> None:
    doc_a = make_document(text="texto identico aqui", source_uri="u1")
    doc_b = make_document(text="texto identico aqui", source_uri="u2")
    doc_c = make_document(text="texto completamente diferente", source_uri="u3")
    keys = [GroupingKeys(document_id=d.document_id) for d in (doc_a, doc_b, doc_c)]
    groups = build_groups([doc_a, doc_b, doc_c], keys)
    members_by_group = list(groups.values())
    grouped_pair = {doc_a.document_id, doc_b.document_id}
    assert any(grouped_pair <= members for members in members_by_group)
    assert not any(
        {doc_a.document_id, doc_c.document_id} <= members for members in members_by_group
    )


def test_build_groups_clusters_by_process_number() -> None:
    doc_a = make_document(text="texto A", source_uri="u1")
    doc_b = make_document(text="texto B totalmente distinto", source_uri="u2")
    keys = [
        GroupingKeys(document_id=doc_a.document_id, normalized_process_number="0001234"),
        GroupingKeys(document_id=doc_b.document_id, normalized_process_number="0001234"),
    ]
    groups = build_groups([doc_a, doc_b], keys)
    assert len(groups) == 1


def test_assign_splits_respects_eligibility() -> None:
    docs = [
        make_document(text=f"documento numero {i} com texto variado", source_uri=f"u{i}")
        for i in range(10)
    ]
    train_only_ids = frozenset(d.document_id for d in docs[:5])
    eval_ids = frozenset(d.document_id for d in docs[5:])
    groups = {d.document_id: frozenset({d.document_id}) for d in docs}

    assignment = assign_splits(
        groups,
        train_eligible=train_only_ids | eval_ids,
        evaluation_eligible=eval_ids,
        seed=42,
    )

    # Train-only documents must never land in val/test.
    assert train_only_ids.isdisjoint(assignment.val_ids)
    assert train_only_ids.isdisjoint(assignment.test_ids)


def test_assign_splits_is_deterministic() -> None:
    docs = [make_document(text=f"doc {i} texto", source_uri=f"u{i}") for i in range(20)]
    all_ids = frozenset(d.document_id for d in docs)
    groups = {d.document_id: frozenset({d.document_id}) for d in docs}

    first = assign_splits(groups, train_eligible=all_ids, evaluation_eligible=all_ids, seed=7)
    second = assign_splits(groups, train_eligible=all_ids, evaluation_eligible=all_ids, seed=7)
    assert first == second


def test_validate_split_leakage_detects_group_spanning_splits() -> None:
    doc_a = make_document(text="grupo compartilhado", source_uri="u1")
    doc_b = make_document(text="grupo compartilhado", source_uri="u2")
    groups = {doc_a.document_id: frozenset({doc_a.document_id, doc_b.document_id})}
    assignment = SplitAssignment(
        train_ids=frozenset({doc_a.document_id}),
        val_ids=frozenset({doc_b.document_id}),
        test_ids=frozenset(),
    )
    problems = validate_split_leakage(assignment, [doc_a, doc_b], groups)
    assert any("spans multiple splits" in p for p in problems)
