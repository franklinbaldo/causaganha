"""Tests for scripts.synthetic_segmenter.transform — the edit-map contract."""

from __future__ import annotations

import pytest

from scripts.synthetic_segmenter.transform import (
    Edit,
    OverlapError,
    apply_edits,
    check_final_invariants,
)


def test_edit_outside_span_before_shifts_label() -> None:
    text = "AAA Ante o exposto BBB"
    anchor = "Ante o exposto"
    start = text.index(anchor)
    labels = [{"category": "dispositivo_abertura", "start": start, "end": start + len(anchor)}]
    # Replace "AAA " (4 chars) with "XX" (2 chars) — a 2-char shrink before the span.
    result = apply_edits(text, labels, [Edit(0, 4, "XX")])
    assert result.text == "XXAnte o exposto BBB"
    assert result.text[result.labels[0]["start"] : result.labels[0]["end"]] == anchor


def test_edit_outside_span_after_does_not_shift_label() -> None:
    text = "Ante o exposto BBB"
    labels = [{"category": "dispositivo_abertura", "start": 0, "end": 14}]
    result = apply_edits(text, labels, [Edit(15, 18, "CCCCC")])
    assert result.labels[0]["start"] == 0
    assert result.labels[0]["end"] == 14
    assert result.text[0:14] == "Ante o exposto"


def test_edit_covering_span_reanchors_to_replacement() -> None:
    text = "AAA Ante o exposto BBB"
    labels = [{"category": "dispositivo_abertura", "start": 4, "end": 19}]
    result = apply_edits(text, labels, [Edit(4, 19, "Diante do exposto")])
    span = result.labels[0]
    assert result.text[span["start"] : span["end"]] == "Diante do exposto"


def test_edit_inside_span_shifts_end_only() -> None:
    text = "Ante o exposto"
    labels = [{"category": "dispositivo_abertura", "start": 0, "end": 14}]
    # Replace "exposto" (7 chars) with "exposto supra" (13 chars) INSIDE the span.
    result = apply_edits(text, labels, [Edit(7, 14, "exposto supra")])
    span = result.labels[0]
    assert span["start"] == 0
    assert result.text[span["start"] : span["end"]] == "Ante o exposto supra"


def test_partial_overlap_raises() -> None:
    text = "Ante o exposto BBB"
    labels = [{"category": "dispositivo_abertura", "start": 0, "end": 14}]
    # Edit spans [10, 18) — crosses the label's end (14) without fully covering it.
    with pytest.raises(OverlapError):
        apply_edits(text, labels, [Edit(10, 18, "xxxxxxxx")])


def test_overlapping_edits_rejected() -> None:
    text = "AAAABBBBCCCC"
    with pytest.raises(ValueError, match="overlapping edits"):
        apply_edits(text, [], [Edit(0, 5, "X"), Edit(3, 8, "Y")])


def test_out_of_bounds_edit_rejected() -> None:
    text = "short"
    with pytest.raises(ValueError, match="out of bounds"):
        apply_edits(text, [], [Edit(0, 100, "X")])


def test_multiple_edits_compound_shifts_correctly() -> None:
    text = "AAA relatorio_inicio BBB Ante o exposto CCC"
    anchor_a = "relatorio_inicio"
    anchor_b = "Ante o exposto"
    start_a = text.index(anchor_a)
    start_b = text.index(anchor_b)
    labels = [
        {"category": "relatorio_inicio", "start": start_a, "end": start_a + len(anchor_a)},
        {"category": "dispositivo_abertura", "start": start_b, "end": start_b + len(anchor_b)},
    ]
    bbb_start = text.index("BBB")
    result = apply_edits(
        text,
        labels,
        [Edit(0, 4, "XX"), Edit(bbb_start, bbb_start + 3, "Y")],
    )
    surfaces = {result.text[label["start"] : label["end"]] for label in result.labels}
    assert surfaces == {anchor_a, anchor_b}


def test_check_final_invariants_clean_record() -> None:
    text = "Ante o exposto, julgo procedente."
    labels = [{"category": "dispositivo_abertura", "start": 0, "end": 14}]
    assert check_final_invariants(text, labels) == []


def test_check_final_invariants_catches_bad_offsets() -> None:
    text = "short"
    labels = [{"category": "x", "start": 3, "end": 100}]
    problems = check_final_invariants(text, labels)
    assert len(problems) == 1
    assert "bad offsets" in problems[0]


def test_check_final_invariants_catches_overlap() -> None:
    text = "AAAAAAAAAA"
    labels = [
        {"category": "a", "start": 0, "end": 5},
        {"category": "b", "start": 3, "end": 8},
    ]
    problems = check_final_invariants(text, labels)
    assert len(problems) == 1
    assert "overlaps" in problems[0]
