"""Behavioral checks for ordered cases, overlap handling and experiment scoring."""

from __future__ import annotations

import numpy as np
import pytest

from scripts.spike_case_tournament import (
    Case,
    Document,
    catalogue,
    classification_metrics,
    external_training,
    first_match,
    fold_for,
    generate_cases,
    match_matrix,
    optimize_list,
    paired_comparison,
    prepare_gold,
)


def test_first_matching_case_decides_and_unmatched_document_abstains():
    matches = np.array([[True, True], [False, True], [False, False]])
    actions = np.array([1, 2])
    assert first_match(matches, (0, 1), actions).tolist() == [1, 2, 0]
    assert first_match(matches, (1, 0), actions).tolist() == [2, 2, 0]


def test_permutation_search_changes_order_without_changing_members():
    matches = np.array([[True, True], [True, True], [True, False]])
    actions = np.array([1, 2])
    labels = np.array([2, 2, 1])
    order = optimize_list(matches, labels, actions, initial=(0, 1), fixed_members=True)
    assert order == (1, 0)
    assert first_match(matches, order, actions).tolist() == labels.tolist()


def test_cases_apply_conjunction_exclusion_scope_and_negation():
    t = catalogue()
    cases = [
        Case(
            "scoped",
            "procedente",
            ("proc_julgo_procedente",),
            scope="dispositivo",
            no_negation=True,
        ),
        Case("and", "procedente", ("proc_julgo_procedente", "proc_condeno_reu")),
        Case("exclude", "procedente", ("proc_condeno_reu",), ("parcial_parcialmente_proc",)),
    ]
    docs = [
        Document("cited", "Antes: julgo procedente. Ante o exposto, julgo improcedente.", ""),
        Document("negated", "Ante o exposto, não julgo procedente o pedido.", ""),
        Document("positive", "Ante o exposto, julgo procedente e condeno o réu.", ""),
        Document("partial", "Julgo parcialmente procedente e condeno o réu.", ""),
        Document("no_anchor", "Condeno o réu.", ""),
    ]
    matrix = match_matrix(docs, cases, t)
    assert matrix[:, 0].tolist() == [False, False, True, False, False]
    assert matrix[:, 1].tolist() == [False, False, True, False, False]
    assert matrix[:, 2].tolist() == [False, False, True, False, True]


def test_negation_guard_accepts_later_unnegated_occurrence():
    t = catalogue()
    case = Case("guard", "procedente", ("proc_julgo_procedente",), no_negation=True)
    doc = Document("1", "Não julgo procedente o anterior. Agora julgo procedente o pedido.", "")
    assert match_matrix([doc], [case], t)[0, 0]


def test_generated_conditions_use_only_existing_regex_catalogue():
    t = catalogue()
    ids = {r.pattern_id for rules in t.categories.values() for r in rules}
    cases = generate_cases(t)
    assert len({c.case_id for c in cases}) == len(cases)
    assert any(len(c.all_of) > 1 for c in cases)
    assert any(c.none_of for c in cases)
    for case in cases:
        assert set(case.all_of + case.none_of) <= ids


def gold_row(doc_id, text, label):
    return {"intimation_id": doc_id, "texto": text, "outcome": label, "court": "TJRO"}


def test_gold_deduplicates_whitespace_and_excludes_conflicting_groups():
    rows = [
        gold_row(1, "Texto A", "procedente"),
        gold_row(2, "Texto  A", "procedente"),
        gold_row(3, "Texto B", "procedente"),
        gold_row(4, "Texto B", "improcedente"),
    ]
    docs, audit = prepare_gold(rows)
    assert len(docs) == 1
    assert docs[0].label == "procedente"
    assert audit["conflicting_groups_excluded"] == 1
    assert fold_for(Document("x", "Texto A", ""), 1697) == fold_for(docs[0], 1697)


def test_external_training_excludes_all_gold_ids_and_normalized_texts():
    gold = [gold_row(1, "Texto A", "procedente"), gold_row(2, "Texto B", "improcedente")]
    rows = [
        {"doc_id": "1", "texto": "Different text"},
        {"doc_id": "3", "texto": "Texto   B"},
        {"doc_id": "4", "texto": "Ante o exposto, julgo procedente o pedido."},
        {"doc_id": "5", "texto": "Ante o exposto, julgo procedente o pedido."},
    ]
    docs, audit = external_training(rows, gold)
    assert [d.doc_id for d in docs] == ["4"]
    assert docs[0].label == "procedente"
    assert audit["excluded_overlap_empty_or_duplicate"] == 3


def test_external_training_fails_if_no_independent_examples_remain():
    with pytest.raises(ValueError, match="No disjoint"):
        external_training([{"doc_id": "1", "texto": "A"}], [gold_row(1, "A", "procedente")])


def test_metrics_keep_abstentions_separate_from_wrong_answers():
    m = classification_metrics(
        ["procedente", "improcedente", "unknown", "procedente"],
        ["procedente", "procedente", "unknown", "unknown"],
        ["procedente", "improcedente"],
    )
    assert m["covered"] == 2
    assert m["correct_answered"] == 1
    assert m["errors_answered"] == 1
    assert m["selective_precision"] == 0.5
    assert m["utility_per_document"] == -0.25
    assert m["per_class"]["procedente"]["fn"] == 1


def test_search_is_deterministic_and_leaves_input_unchanged():
    matches = np.array([[True, False], [True, False], [False, True], [False, True]])
    before = matches.copy()
    gold = np.array([1, 1, 2, 2])
    actions = np.array([1, 2])
    a = optimize_list(matches, gold, actions)
    b = optimize_list(matches, gold, actions)
    assert a == b
    assert first_match(matches, a, actions).tolist() == gold.tolist()
    assert np.array_equal(matches, before)


def test_paired_comparison_counts_abstention_tradeoff_and_is_reproducible():
    docs = [Document("1", "A", "procedente"), Document("2", "B", "improcedente")]
    reference = ["procedente", "procedente"]
    candidate = ["unknown", "improcedente"]
    result = paired_comparison(docs, reference, candidate, 1697)
    assert result["utility_improved_documents"] == 1
    assert result["utility_worsened_documents"] == 1
    assert result["mean_utility_delta"] == 1.0  # (-1 + 3) / 2
    assert result == paired_comparison(docs, reference, candidate, 1697)
