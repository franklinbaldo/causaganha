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
