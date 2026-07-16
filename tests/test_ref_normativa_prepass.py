"""Tests for scripts.ref_normativa_prepass.

No dedicated test file existed before this — coverage lived only in
integration tests (test_segment_decision.py, test_reconstruct_regions.py).
Added alongside a real bug fix found via manual audit of real TJRO text.
"""

from __future__ import annotations

from scripts.ref_normativa_prepass import extract_ref_normativa, merge_with_opf_spans


def test_extracts_article_citation() -> None:
    spans = extract_ref_normativa("nos termos do art. 927 do CPC")
    categories = {s["category"] for s in spans}
    assert categories == {"ref_normativa"}
    surfaces = {"nos termos do art. 927 do CPC"[s["start"] : s["end"]] for s in spans}
    assert "art. 927" in surfaces
    assert "CPC" in surfaces


def test_extracts_law_citation() -> None:
    text = "art. 55 da Lei nº 9.099/95"
    spans = extract_ref_normativa(text)
    surfaces = {text[s["start"] : s["end"]] for s in spans}
    assert "Lei nº 9.099/95" in surfaces


def test_extracts_sumula_citation() -> None:
    text = "Aplica-se a Súmula 331 do TST ao caso."
    spans = extract_ref_normativa(text)
    surfaces = {text[s["start"] : s["end"]] for s in spans}
    assert "Súmula 331" in surfaces


def test_article_number_above_999_is_not_truncated() -> None:
    r"""Regression: real bug found via manual audit of a TJRO SENTENÇA
    sample. Article numbers above 999 use a Brazilian thousands-separator
    period ("art. 1.000", "art. 1.037" — CPC/2015 has 1072 articles). The
    original pattern (\d+) stopped at the period, truncating the span to
    "art. 1" — confirmed as a real, non-rare bug (~5% of "art."-citations
    in a real sample), not a hypothetical edge case.
    """
    text = "Ante a preclusão lógica (art. 1.000, do CPC), a decisão transita em julgado."
    spans = extract_ref_normativa(text)
    surfaces = {text[s["start"] : s["end"]] for s in spans}
    assert "art. 1.000" in surfaces
    assert "art. 1" not in surfaces


def test_article_number_below_1000_still_works() -> None:
    text = "com fundamento no art. 487, inciso III, do CPC"
    spans = extract_ref_normativa(text)
    surfaces = {text[s["start"] : s["end"]] for s in spans}
    assert any(s.startswith("art. 487") for s in surfaces)


def test_spelled_out_inciso_is_captured_in_full() -> None:
    """Regression: found via manual audit alongside the thousands-separator
    fix. The original continuation pattern (a bare char class) matched
    only the leading "i" of "inciso" (since "i" is a valid roman-numeral
    character), truncating "art. 5º, inciso II, alínea b" down to just
    "art. 5º, i" — a much worse truncation than the thousands-separator
    bug, since the result isn't even a coherent citation surface.
    """
    text = "art. 5º, inciso II, alínea b, do CPC"
    spans = extract_ref_normativa(text)
    surfaces = {text[s["start"] : s["end"]] for s in spans}
    assert "art. 5º, inciso II, alínea b" in surfaces
    assert not any(s.endswith(", i") for s in surfaces)


def test_spelled_out_paragrafo_unico_is_captured() -> None:
    text = "nos termos do art. 927, parágrafo único, do CPC"
    spans = extract_ref_normativa(text)
    surfaces = {text[s["start"] : s["end"]] for s in spans}
    assert "art. 927, parágrafo único" in surfaces


def test_bare_roman_numeral_shorthand_still_works() -> None:
    """Brazilian legal writing commonly drops the word "inciso" entirely
    ("art. 924, II" meaning "art. 924, inciso II") — this shorthand must
    keep working alongside the spelled-out form, not just the fix.
    """
    text = "art. 924, II do novo Código de Processo Civil"
    spans = extract_ref_normativa(text)
    surfaces = {text[s["start"] : s["end"]] for s in spans}
    assert "art. 924, II" in surfaces


def test_multiple_incisos_joined_by_e_are_captured() -> None:
    text = "art. 487, incisos I e II, do CPC"
    spans = extract_ref_normativa(text)
    surfaces = {text[s["start"] : s["end"]] for s in spans}
    assert "art. 487, incisos I e II" in surfaces


def test_merge_keeps_model_span_over_overlapping_regex_span() -> None:
    text = "Nos termos do art. 927 do CPC, julgo procedente."
    start = text.find("art. 927")
    model_span = {"category": "fundamentacao_legal", "start": start, "end": start + len("art. 927")}
    ref_spans = extract_ref_normativa(text)
    merged = merge_with_opf_spans([model_span], ref_spans)
    fund = [s for s in merged if s["category"] == "fundamentacao_legal"]
    assert len(fund) == 1


def test_merge_keeps_non_overlapping_ref_span() -> None:
    text = "Aplica-se a Súmula 331 do TST ao caso."
    merged = merge_with_opf_spans([], extract_ref_normativa(text))
    assert any(s["category"] == "ref_normativa" for s in merged)
