"""Tests for scripts.synthetic_segmenter.validators."""

from __future__ import annotations

from scripts.synthetic_segmenter.validators import load_label_space_categories, validate_record


_CATEGORIES = {"dispositivo_abertura", "resultado", "relatorio_inicio", "relatorio_fim"}


def test_clean_record_validates() -> None:
    text = "Ante o exposto, julgo procedente."
    labels = [
        {"category": "dispositivo_abertura", "start": 0, "end": 14},
        {"category": "resultado", "start": 16, "end": 33},
    ]
    assert validate_record(text, labels, _CATEGORIES) == []


def test_unknown_category_rejected() -> None:
    text = "some text"
    labels = [{"category": "not_a_real_category", "start": 0, "end": 4}]
    problems = validate_record(text, labels, _CATEGORIES)
    assert any("not in label space" in p for p in problems)


def test_multiple_dispositivo_abertura_rejected() -> None:
    text = "Ante o exposto Ante o exposto"
    labels = [
        {"category": "dispositivo_abertura", "start": 0, "end": 14},
        {"category": "dispositivo_abertura", "start": 15, "end": 29},
    ]
    problems = validate_record(text, labels, _CATEGORIES)
    assert any("dispositivo_abertura" in p and "exactly one" in p for p in problems)


def test_unmatched_pair_without_flag_flagged() -> None:
    text = "RELATÓRIO some body text here"
    labels = [{"category": "relatorio_inicio", "start": 0, "end": 9}]
    problems = validate_record(text, labels, _CATEGORIES, info={"unmatched_pair": False})
    assert any("unmatched pair" in p for p in problems)


def test_unmatched_pair_with_flag_ok() -> None:
    text = "RELATÓRIO some body text here"
    labels = [{"category": "relatorio_inicio", "start": 0, "end": 9}]
    problems = validate_record(text, labels, _CATEGORIES, info={"unmatched_pair": True})
    assert problems == []


def test_flag_true_but_no_unmatched_pair_flagged() -> None:
    text = "RELATÓRIO body É o relatório."
    labels = [
        {"category": "relatorio_inicio", "start": 0, "end": 9},
        {"category": "relatorio_fim", "start": 15, "end": 29},
    ]
    problems = validate_record(text, labels, _CATEGORIES, info={"unmatched_pair": True})
    assert any("no unmatched pair found" in p for p in problems)


def test_no_info_skips_unmatched_pair_check() -> None:
    text = "RELATÓRIO some body text here"
    labels = [{"category": "relatorio_inicio", "start": 0, "end": 9}]
    assert validate_record(text, labels, _CATEGORIES) == []


def test_bad_offsets_still_caught() -> None:
    text = "short"
    labels = [{"category": "dispositivo_abertura", "start": 0, "end": 999}]
    problems = validate_record(text, labels, _CATEGORIES)
    assert any("bad offsets" in p for p in problems)


def test_load_label_space_categories_excludes_o() -> None:
    parsed = {"span_class_names": ["O", "resultado", "dispositivo_abertura"]}
    assert load_label_space_categories(parsed) == {"resultado", "dispositivo_abertura"}
