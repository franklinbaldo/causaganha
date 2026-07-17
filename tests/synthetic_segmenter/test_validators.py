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


def test_orphaned_fim_without_inicio_rejected() -> None:
    text = "É o relatório."
    labels = [{"category": "relatorio_fim", "start": 0, "end": 14}]
    problems = validate_record(text, labels, _CATEGORIES)
    assert any("orphaned or excess _fim" in p for p in problems)


def test_orphaned_fim_rejected_even_with_unmatched_pair_declared() -> None:
    # unmatched_pair only excuses a dangling _inicio (section runs to EOD),
    # never a _fim with no _inicio at all -- that has no legitimate reading.
    text = "É o relatório."
    labels = [{"category": "relatorio_fim", "start": 0, "end": 14}]
    problems = validate_record(text, labels, _CATEGORIES, info={"unmatched_pair": True})
    assert any("orphaned or excess _fim" in p for p in problems)


def test_more_fim_than_inicio_rejected() -> None:
    text = "RELATÓRIO body É o relatório. É o relatório de novo."
    labels = [
        {"category": "relatorio_inicio", "start": 0, "end": 9},
        {"category": "relatorio_fim", "start": 15, "end": 29},
        {"category": "relatorio_fim", "start": 31, "end": 52},
    ]
    problems = validate_record(text, labels, _CATEGORIES)
    assert any("orphaned or excess _fim" in p for p in problems)


def test_two_dangling_inicio_without_fim_rejected() -> None:
    # unmatched_pair allows at most ONE dangling _inicio (the last section
    # extending to EOD) -- two unmatched _inicio for the same base is a
    # real generator bug, not a legitimate single-EOD-section case.
    text = "RELATÓRIO one RELATÓRIO two"
    labels = [
        {"category": "relatorio_inicio", "start": 0, "end": 9},
        {"category": "relatorio_inicio", "start": 14, "end": 23},
    ]
    problems = validate_record(text, labels, _CATEGORIES, info={"unmatched_pair": True})
    assert any("unbalanced beyond the single-dangling" in p for p in problems)


def test_inverted_pair_fim_before_inicio_rejected() -> None:
    text = "É o relatório. RELATÓRIO"
    labels = [
        {"category": "relatorio_fim", "start": 0, "end": 14},
        {"category": "relatorio_inicio", "start": 15, "end": 24},
    ]
    problems = validate_record(text, labels, _CATEGORIES)
    assert any("inverted pair" in p for p in problems)


def test_balanced_multi_occurrence_pairs_ok() -> None:
    # Two separate relatorio_inicio/_fim occurrences in one document (e.g.
    # a doc that repeats a structural block) is legitimate as long as
    # counts balance and each _fim follows its own _inicio.
    text = "RELATÓRIO a É o relatório. RELATÓRIO b É o relatório."
    labels = [
        {"category": "relatorio_inicio", "start": 0, "end": 9},
        {"category": "relatorio_fim", "start": 12, "end": 26},
        {"category": "relatorio_inicio", "start": 27, "end": 36},
        {"category": "relatorio_fim", "start": 39, "end": 53},
    ]
    assert validate_record(text, labels, _CATEGORIES) == []


def test_load_label_space_categories_excludes_o() -> None:
    parsed = {"span_class_names": ["O", "resultado", "dispositivo_abertura"]}
    assert load_label_space_categories(parsed) == {"resultado", "dispositivo_abertura"}
