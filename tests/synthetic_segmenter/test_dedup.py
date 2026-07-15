"""Tests for scripts.synthetic_segmenter.dedup — hashing and near-duplicate detection."""

from __future__ import annotations

from scripts.synthetic_segmenter.dedup import (
    content_hash,
    find_exact_duplicates,
    find_near_duplicates,
    near_duplicate_ratio,
    normalize_text,
)


def test_normalize_collapses_whitespace_and_case() -> None:
    assert normalize_text("  Ante   o\n\nexposto  ") == "ante o exposto"


def test_content_hash_ignores_incidental_whitespace() -> None:
    a = content_hash("Ante o exposto,\njulgo procedente.")
    b = content_hash("ante o exposto,   julgo procedente.")
    assert a == b


def test_content_hash_differs_for_different_text() -> None:
    a = content_hash("julgo procedente")
    b = content_hash("julgo improcedente")
    assert a != b


def test_near_duplicate_ratio_identical_is_one() -> None:
    assert near_duplicate_ratio("same text here", "same text here") == 1.0


def test_near_duplicate_ratio_unrelated_is_low() -> None:
    ratio = near_duplicate_ratio(
        "Ante o exposto, dou parcial provimento ao recurso.",
        "É o relatório. Passo ao voto sobre honorários.",
    )
    assert ratio < 0.5


def test_find_exact_duplicates() -> None:
    records = {
        "a": "Ante o exposto, julgo procedente.",
        "b": "ante o exposto,   julgo procedente.",  # same after normalization
        "c": "completely different text about something else entirely",
    }
    dupes = find_exact_duplicates(records)
    assert dupes == [("a", "b")]


def test_find_exact_duplicates_none_when_all_distinct() -> None:
    records = {"a": "one thing", "b": "another thing", "c": "a third thing"}
    assert find_exact_duplicates(records) == []


def test_find_near_duplicates_above_threshold() -> None:
    records = {
        "a": "Ante o exposto, dou parcial provimento ao recurso interposto.",
        "b": "Ante o exposto, dou parcial provimento ao recurso apresentado.",
        "c": "É o relatório. Sem preliminares a apreciar neste feito.",
    }
    near = find_near_duplicates(records, threshold=0.85)
    ids = {(a, b) for a, b, _ratio in near}
    assert ("a", "b") in ids
    assert not any("c" in pair for pair in ids)


def test_find_near_duplicates_sorted_descending() -> None:
    records = {
        "a": "aaaaaaaaaa",
        "b": "aaaaaaaaab",
        "c": "aaaaaaabbb",
    }
    near = find_near_duplicates(records, threshold=0.0)
    ratios = [r for _a, _b, r in near]
    assert ratios == sorted(ratios, reverse=True)
