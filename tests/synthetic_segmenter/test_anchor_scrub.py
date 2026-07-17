"""Tests for scripts.synthetic_segmenter.anchor_scrub."""

from __future__ import annotations

import pytest

from scripts.synthetic_segmenter.anchor_scrub import (
    ExcerptContainsAnchorError,
    find_anchor_occurrences,
    neutralize_excerpt,
    scrub_excerpt,
    scrub_excerpt_with_occurrences,
)


def test_find_anchor_occurrences_detects_known_phrase() -> None:
    text = "A sentença recorrida registrou: Ante o exposto, julgo procedente o pedido."
    occurrences = find_anchor_occurrences(text)
    categories = {occ["category"] for occ in occurrences}
    assert "dispositivo_abertura" in categories
    assert "resultado" in categories


def test_find_anchor_occurrences_offsets_are_exact() -> None:
    text = "prefixo Ante o exposto sufixo"
    occurrences = find_anchor_occurrences(text)
    hit = next(occ for occ in occurrences if occ["category"] == "dispositivo_abertura")
    assert text[hit["start"] : hit["end"]] == "Ante o exposto"


def test_find_anchor_occurrences_empty_for_clean_text() -> None:
    text = "Os documentos juntados aos autos demonstram a plausibilidade do direito alegado."
    assert find_anchor_occurrences(text) == []


def test_neutralize_excerpt_wraps_anchor_in_reported_speech() -> None:
    """The literal anchor stays (same shape as quoted_dispositivo) — it's the
    surrounding frame that turns it non-operative, not lexical removal
    (detection is lexical, so a wrapped anchor is still "findable"; what
    matters is that a downstream renderer never labels it, which is a
    labeling-time decision this module doesn't make).
    """
    text = "A sentença registrou: Ante o exposto, julgo procedente o pedido."
    neutralized = neutralize_excerpt(text)
    assert "Ante o exposto" in neutralized
    assert "o excerto registra que" in neutralized


def test_neutralize_excerpt_is_noop_on_clean_text() -> None:
    text = "Nenhuma âncora aqui."
    assert neutralize_excerpt(text) == text


def test_neutralize_excerpt_handles_multiple_occurrences() -> None:
    text = "Primeiro: Ante o exposto. Depois: É o relatório."
    neutralized = neutralize_excerpt(text)
    assert neutralized.count("o excerto registra que") == 2


def test_scrub_excerpt_discard_mode_raises_on_anchor() -> None:
    text = "Ante o exposto, julgo procedente o pedido."
    with pytest.raises(ExcerptContainsAnchorError):
        scrub_excerpt(text, mode="discard")


def test_scrub_excerpt_discard_mode_passes_clean_text() -> None:
    text = "Nenhuma âncora aqui."
    assert scrub_excerpt(text, mode="discard") == text


def test_scrub_excerpt_promote_hard_negative_leaves_text_unchanged() -> None:
    text = "Ante o exposto, julgo procedente o pedido."
    assert scrub_excerpt(text, mode="promote_hard_negative") == text


def test_scrub_excerpt_default_mode_is_neutralize() -> None:
    text = "Ante o exposto, julgo procedente o pedido."
    assert scrub_excerpt(text) == neutralize_excerpt(text)


def test_scrub_excerpt_unknown_mode_raises() -> None:
    with pytest.raises(ValueError, match="unknown scrub mode"):
        scrub_excerpt("texto", mode="bogus")


def test_scrub_excerpt_with_occurrences_promote_hard_negative_surfaces_categories() -> None:
    # This is the fix for the bug where scrub_excerpt(mode="promote_hard_negative")
    # discarded the found occurrences entirely, leaving the caller no way
    # to record which categories were actually promoted as hard negatives.
    text = "Ante o exposto, julgo procedente o pedido."
    out_text, occurrences = scrub_excerpt_with_occurrences(text, mode="promote_hard_negative")
    assert out_text == text
    categories = {occ["category"] for occ in occurrences}
    assert "dispositivo_abertura" in categories
    assert "resultado" in categories


def test_scrub_excerpt_with_occurrences_discard_mode_matches_scrub_excerpt() -> None:
    text = "Nenhuma âncora aqui."
    out_text, occurrences = scrub_excerpt_with_occurrences(text, mode="discard")
    assert out_text == text
    assert occurrences == []


def test_scrub_excerpt_with_occurrences_neutralize_returns_scrubbed_text() -> None:
    text = "Ante o exposto, julgo procedente o pedido."
    out_text, occurrences = scrub_excerpt_with_occurrences(text, mode="neutralize")
    assert out_text == neutralize_excerpt(text)
    categories = {occ["category"] for occ in occurrences}
    assert "dispositivo_abertura" in categories


def test_scrub_excerpt_is_a_thin_wrapper_over_with_occurrences() -> None:
    text = "Ante o exposto, julgo procedente o pedido."
    for mode in ("neutralize", "promote_hard_negative"):
        expected_text, _occurrences = scrub_excerpt_with_occurrences(text, mode=mode)
        assert scrub_excerpt(text, mode=mode) == expected_text

    clean_text = "Nenhuma âncora aqui."
    expected_clean, _occ = scrub_excerpt_with_occurrences(clean_text, mode="discard")
    assert scrub_excerpt(clean_text, mode="discard") == expected_clean


def test_neutralized_excerpt_never_reintroduces_anchor_after_double_pass() -> None:
    text = "Ante o exposto, julgo procedente o pedido. É o relatório."
    once = neutralize_excerpt(text)
    twice = neutralize_excerpt(once)
    assert once == twice
