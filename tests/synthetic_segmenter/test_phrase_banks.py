"""Tests for scripts.synthetic_segmenter.phrase_banks."""

from __future__ import annotations

import pytest

from scripts.synthetic_segmenter.phrase_banks import (
    FUSED_CUSTAS_HONORARIOS_TEMPLATES,
    PAIR_PHRASES,
    REF_NORMATIVA_FILLER_PHRASES,
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


def test_ref_normativa_absent_from_anchor_phrase_banks() -> None:
    """ref_normativa IS trained (RFC 0001, reversed 2026-07-16) but is not
    an anchor-phrase category: renderer.py bootstraps it via regex over
    fully-rendered text (see REF_NORMATIVA_FILLER_PHRASES / render()'s
    docstring), the same way real gold sources it, rather than a
    hand-picked phrase-bank entry.
    """
    assert "ref_normativa" not in SINGLE_ANCHOR_PHRASES
    assert "ref_normativa" not in PAIR_PHRASES


def test_ref_normativa_filler_phrases_nonempty_and_yield_citations() -> None:
    from scripts.ref_normativa_prepass import extract_ref_normativa

    assert REF_NORMATIVA_FILLER_PHRASES
    for phrase in REF_NORMATIVA_FILLER_PHRASES:
        assert extract_ref_normativa(phrase), f"{phrase!r} yields no ref_normativa match"


def test_fused_custas_honorarios_templates_have_all_fragments() -> None:
    assert FUSED_CUSTAS_HONORARIOS_TEMPLATES
    for template in FUSED_CUSTAS_HONORARIOS_TEMPLATES:
        for key in (
            "custas_inicio",
            "custas_fim",
            "connector",
            "honorarios_inicio",
            "honorarios_fim",
        ):
            assert template[key], f"{template!r} missing/empty {key!r}"


def test_preliminar_fim_includes_round_a_variants() -> None:
    fim_phrases = PAIR_PHRASES["preliminar"]["fim"]
    assert "Preliminar acolhida." in fim_phrases
    assert "afasto a preliminar suscitada, submetendo-a ao Colegiado." in fim_phrases
