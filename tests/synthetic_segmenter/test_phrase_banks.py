"""Tests for scripts.synthetic_segmenter.phrase_banks."""

from __future__ import annotations

import pytest

from scripts.synthetic_segmenter.phrase_banks import (
    PAIR_PHRASES,
    RESULTADO_PHRASES,
    SINGLE_ANCHOR_PHRASES,
    resultado_phrase,
)


def test_every_pair_category_has_inicio_and_fim() -> None:
    for base_name, phrases in PAIR_PHRASES.items():
        assert phrases["inicio"], f"{base_name} has no inicio variants"
        assert phrases["fim"], f"{base_name} has no fim variants"


def test_single_anchor_categories_nonempty() -> None:
    for category, phrases in SINGLE_ANCHOR_PHRASES.items():
        assert phrases, f"{category} has no phrase variants"


def test_resultado_phrase_known_outcome() -> None:
    phrase = resultado_phrase("procedente")
    assert phrase in RESULTADO_PHRASES["procedente"]


def test_resultado_phrase_unknown_outcome_raises() -> None:
    with pytest.raises(ValueError, match="no resultado phrase"):
        resultado_phrase("not_a_real_outcome")


def test_ref_normativa_deliberately_absent() -> None:
    """ref_normativa is excluded from the trainable v7 label space (RFC
    0001) even though the guideline still documents it conceptually.
    """
    assert "ref_normativa" not in SINGLE_ANCHOR_PHRASES
    assert "ref_normativa" not in PAIR_PHRASES
