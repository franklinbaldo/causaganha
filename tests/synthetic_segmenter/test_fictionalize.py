"""Tests for scripts.synthetic_segmenter.fictionalize."""

from __future__ import annotations

from scripts.synthetic_segmenter.fictionalize import fictionalize_excerpt
from scripts.synthetic_segmenter.identities import generate_identities


def test_process_number_is_replaced() -> None:
    identities = generate_identities(1)
    text = "Trata-se do processo 7000109-66.2024.8.22.0000 distribuído em Porto Velho."
    result = fictionalize_excerpt(text, identities)
    assert "7000109-66.2024.8.22.0000" not in result
    assert identities.numero_processo in result


def test_oab_numbers_are_replaced() -> None:
    identities = generate_identities(1)
    text = "Advogado(a): Eduardo Queiroga (OAB/RO 13431)."
    result = fictionalize_excerpt(text, identities)
    assert "OAB/RO 13431" not in result
    assert identities.oab_autor in result


def test_multiple_oab_occurrences_alternate_identities() -> None:
    identities = generate_identities(1)
    text = "Autor: OAB/RO 1000. Réu: OAB/SP 2000."
    result = fictionalize_excerpt(text, identities)
    assert identities.oab_autor in result
    assert identities.oab_reu in result


def test_legal_citations_are_untouched() -> None:
    identities = generate_identities(1)
    text = "conforme dispõe o art. 927 do CPC, aplica-se o precedente."
    result = fictionalize_excerpt(text, identities)
    assert result == text


def test_clean_text_is_unchanged() -> None:
    identities = generate_identities(1)
    text = "Os documentos juntados aos autos demonstram a plausibilidade do direito."
    assert fictionalize_excerpt(text, identities) == text


def test_fictionalization_is_deterministic_for_same_identity_seed() -> None:
    text = "Processo 7000109-66.2024.8.22.0000, OAB/RO 13431."
    first = fictionalize_excerpt(text, generate_identities(42))
    second = fictionalize_excerpt(text, generate_identities(42))
    assert first == second
