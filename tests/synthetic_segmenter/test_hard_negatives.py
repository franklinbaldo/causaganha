"""Tests for scripts.synthetic_segmenter.hard_negatives."""

from __future__ import annotations

import pytest

from scripts.synthetic_segmenter.hard_negatives import (
    HARD_NEGATIVE_FAMILIES,
    render_hard_negative,
)


def test_all_declared_families_render() -> None:
    for family in HARD_NEGATIVE_FAMILIES:
        text = render_hard_negative(family)
        assert isinstance(text, str)
        assert text.strip()


def test_quoted_dispositivo_contains_the_trap_phrase() -> None:
    text = render_hard_negative("quoted_dispositivo")
    assert "ante o exposto" in text.lower()


def test_reported_prior_outcome_contains_the_trap_phrase() -> None:
    text = render_hard_negative("reported_prior_outcome")
    assert "julgou procedente" in text.lower() or "julgo procedente" in text.lower()


def test_preliminar_in_decisorio_summary_contains_the_trap_phrase() -> None:
    text = render_hard_negative("preliminar_in_decisorio_summary")
    assert "preliminar" in text.lower()


def test_unknown_family_raises() -> None:
    with pytest.raises(ValueError, match="unknown hard_negative_family"):
        render_hard_negative("not_a_real_family")
