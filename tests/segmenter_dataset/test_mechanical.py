from __future__ import annotations

from segmenter_dataset.mechanical import (
    check_final_invariants,
    validate_ontology_membership,
    validate_pairs,
    validate_record,
    validate_single_anchor_duplicates,
)
from segmenter_dataset.schemas import Label


CATEGORIES = {"cabecalho_inicio", "cabecalho_fim", "dispositivo_abertura", "resultado"}


def test_check_final_invariants_flags_out_of_bounds() -> None:
    text = "0123456789"
    labels = [Label(start=5, end=20, category="x")]
    problems = check_final_invariants(text, labels)
    assert any("exceeds text length" in p for p in problems)


def test_check_final_invariants_flags_overlap() -> None:
    text = "0123456789"
    labels = [
        Label(start=0, end=5, category="a"),
        Label(start=3, end=8, category="b"),
    ]
    problems = check_final_invariants(text, labels)
    assert any("overlaps previous span" in p for p in problems)


def test_check_final_invariants_clean_record() -> None:
    text = "0123456789"
    labels = [Label(start=0, end=5, category="a"), Label(start=5, end=10, category="b")]
    assert check_final_invariants(text, labels) == []


def test_validate_pairs_orphan_fim() -> None:
    labels = [Label(start=0, end=5, category="cabecalho_fim")]
    problems = validate_pairs(labels)
    assert any("orphaned or excess _fim" in p for p in problems)


def test_validate_pairs_inverted_pair() -> None:
    labels = [
        Label(start=10, end=15, category="cabecalho_inicio"),
        Label(start=0, end=5, category="cabecalho_fim"),
    ]
    problems = validate_pairs(labels)
    assert any("inverted pair" in p for p in problems)


def test_validate_pairs_single_dangling_inicio_requires_declaration() -> None:
    labels = [Label(start=0, end=5, category="cabecalho_inicio")]
    problems = validate_pairs(labels, declared_unmatched=False)
    assert any("no declared allowed-unmatched reason" in p for p in problems)

    problems_declared = validate_pairs(labels, declared_unmatched=True)
    assert problems_declared == []


def test_validate_pairs_interleaved_inversion_is_a_known_gap_not_caught() -> None:
    """Locks in the module-docstring's documented #832-inherited weakness.

    ``_inicio`` at [10, 20] and ``_fim`` at [15, 100]: the true nesting-order
    pairing is 20->15 (inverted, invalid), but sorted-start ``zip`` pairs
    10->15 and 20->100 instead, both of which look valid in isolation. This
    test is not asserting desired behavior — it documents the current gap so
    a future fix (pairing by nesting depth) has a regression test to flip
    green, and so this limitation can't silently regress further un-noticed.
    """
    labels = [
        Label(start=10, end=11, category="cabecalho_inicio"),
        Label(start=20, end=21, category="cabecalho_inicio"),
        Label(start=15, end=16, category="cabecalho_fim"),
        Label(start=100, end=101, category="cabecalho_fim"),
    ]
    assert validate_pairs(labels) == []


def test_validate_pairs_balanced_ok() -> None:
    labels = [
        Label(start=0, end=5, category="cabecalho_inicio"),
        Label(start=5, end=10, category="cabecalho_fim"),
    ]
    assert validate_pairs(labels) == []


def test_validate_ontology_membership() -> None:
    labels = [Label(start=0, end=5, category="not_in_ontology")]
    problems = validate_ontology_membership(labels, CATEGORIES)
    assert any("not_in_ontology" in p for p in problems)


def test_validate_single_anchor_duplicates_rejected_by_default() -> None:
    labels = [
        Label(start=0, end=5, category="dispositivo_abertura"),
        Label(start=10, end=15, category="dispositivo_abertura"),
    ]
    problems = validate_single_anchor_duplicates(labels)
    assert any("dispositivo_abertura" in p for p in problems)


def test_validate_single_anchor_duplicates_allowed_when_permitted() -> None:
    labels = [
        Label(start=0, end=5, category="resultado"),
        Label(start=10, end=15, category="resultado"),
    ]
    assert validate_single_anchor_duplicates(labels, allow_multiple=frozenset({"resultado"})) == []


def test_validate_record_composes_all_checks() -> None:
    text = "0" * 20
    labels = [
        Label(start=0, end=5, category="cabecalho_inicio"),
        Label(start=5, end=10, category="cabecalho_fim"),
    ]
    assert validate_record(text, labels, CATEGORIES) == []
