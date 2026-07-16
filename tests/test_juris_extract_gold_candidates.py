"""Tests for scripts.juris_extract_gold_candidates."""

from __future__ import annotations

from scripts.juris_extract_gold_candidates import (
    extract_candidate,
    extract_internal_candidate,
    extract_preliminar_candidate,
)
from scripts.synthetic_segmenter.transform import check_final_invariants


def _row(texto_limpo: str, **extra: object) -> dict:
    return {
        "id_documento": 123,
        "nr_processo": "0001234-56.2020.8.22.0001",
        "classe_judicial": "APELAÇÃO CÍVEL",
        "orgao": "1ª Câmara Cível",
        "relator": "FULANO DE TAL",
        "texto_limpo": texto_limpo,
        **extra,
    }


def test_voto_with_regular_closing_matches_both_anchors() -> None:
    row = _row("VOTO DESEMBARGADOR FULANO. Presentes os pressupostos. É como voto.")
    candidate = extract_candidate(row, "VOTO")
    assert candidate is not None
    categories = [lab["category"] for lab in candidate["label"]]
    assert categories == ["voto_inicio", "voto_fim"]
    assert candidate["info"]["unmatched_pair"] is False


def test_voto_with_juizado_especial_closing_matches() -> None:
    row = _row(
        "VOTO Presentes os pressupostos de admissibilidade, conheço do recurso e, "
        "transitada em julgado, remetam-se os autos à origem."
    )
    candidate = extract_candidate(row, "VOTO")
    assert candidate is not None
    assert candidate["info"]["unmatched_pair"] is False


def test_relatorio_with_lei_9099_dispensation_matches() -> None:
    row = _row(
        "RELATÓRIO Trata-se de recurso. Presentes os pressupostos de admissibilidade, "
        "sendo o relatório dispensado nos termos da Lei nº 9.099/95."
    )
    candidate = extract_candidate(row, "RELATÓRIO")
    assert candidate is not None
    categories = [lab["category"] for lab in candidate["label"]]
    assert categories == ["relatorio_inicio", "relatorio_fim"]


def test_no_inicio_match_is_rejected() -> None:
    row = _row("Texto qualquer que não começa com nenhuma âncora conhecida. É como voto.")
    assert extract_candidate(row, "VOTO") is None


def test_missing_fim_produces_unmatched_pair_candidate() -> None:
    row = _row("VOTO Presentes os pressupostos de admissibilidade, conheço do recurso.")
    candidate = extract_candidate(row, "VOTO")
    assert candidate is not None
    categories = [lab["category"] for lab in candidate["label"]]
    assert categories == ["voto_inicio"]
    assert candidate["info"]["unmatched_pair"] is True


def test_too_short_text_is_rejected() -> None:
    row = _row("VOTO curto.")
    assert extract_candidate(row, "VOTO") is None


def test_noise_at_start_is_rejected_not_just_tail() -> None:
    """Manual audit finding: Word/OpenXML metadata junk can sit right after
    the opening heading, not only at the end — an end-only check misses it.
    """
    row = _row(
        "RELATÓRIO Normal 0 21 false false false PT-BR X-NONE X-NONE LUIZ ALVES "
        "AMORIM recorre da sentença proferida nos autos da ação. É o relatório."
    )
    assert extract_candidate(row, "RELATÓRIO") is None


def test_voto_fim_matches_regardless_of_variable_lead_in() -> None:
    """Manual audit finding: the lead-in before 'remetam-se os autos à origem.'
    varies freely across real documents ("transitada em julgado,"/"Após o
    trânsito em julgado,"/"Com o trânsito em julgado"/"Oportunamente,") —
    only the closing clause is stable, so the phrase bank must not require a
    specific lead-in.
    """
    variants = [
        "VOTO Conheço do recurso. Após o trânsito em julgado, remetam-se os autos à origem.",
        "VOTO Conheço do recurso. Com o trânsito em julgado remetam-se os autos à origem.",
        "VOTO Conheço do recurso. Oportunamente, remetam-se os autos à origem.",
    ]
    for text in variants:
        candidate = extract_candidate(_row(text), "VOTO")
        assert candidate is not None, text
        categories = [lab["category"] for lab in candidate["label"]]
        assert categories == ["voto_inicio", "voto_fim"], text


def test_relatorio_dispensation_matches_lei_n_abbreviation() -> None:
    """Manual audit finding: 'Lei n.' (not just 'Lei nº') is the dominant
    real abbreviation in Juizado Especial relatório-dispensation text.
    """
    row = _row("RELATÓRIO Relatório dispensado, nos termos da Lei n. 9.099/95.")
    candidate = extract_candidate(row, "RELATÓRIO")
    assert candidate is not None
    categories = [lab["category"] for lab in candidate["label"]]
    assert categories == ["relatorio_inicio", "relatorio_fim"]


def test_noisy_tail_is_rejected() -> None:
    row = _row(
        "VOTO Presentes os pressupostos de admissibilidade. É como voto. "
        "21 false false false PT-BR X-NONE X-NONE"
    )
    assert extract_candidate(row, "VOTO") is None


def test_ementa_has_no_fim_and_is_always_unmatched_pair() -> None:
    row = _row("EMENTA Direito civil. Recurso conhecido e provido. Sem condenação em custas.")
    candidate = extract_candidate(row, "EMENTA")
    assert candidate is not None
    categories = [lab["category"] for lab in candidate["label"]]
    assert categories == ["ementa_inicio"]
    assert candidate["info"]["unmatched_pair"] is True


def test_candidate_offsets_are_exact() -> None:
    row = _row("VOTO Presentes os pressupostos de admissibilidade. É como voto.")
    candidate = extract_candidate(row, "VOTO")
    for label in candidate["label"]:
        surface = candidate["text"][label["start"] : label["end"]]
        assert surface == surface.strip()
        assert surface != ""


def test_candidate_passes_final_invariants() -> None:
    row = _row("VOTO Presentes os pressupostos de admissibilidade. É como voto.")
    candidate = extract_candidate(row, "VOTO")
    assert check_final_invariants(candidate["text"], candidate["label"]) == []


def test_candidate_info_preserves_real_source_metadata() -> None:
    row = _row("VOTO Presentes os pressupostos de admissibilidade. É como voto.")
    candidate = extract_candidate(row, "VOTO")
    info = candidate["info"]
    assert info["source"] == "tjro_juris"
    assert info["id_documento"] == 123
    assert info["nr_processo"] == "0001234-56.2020.8.22.0001"
    assert info["doc_type"] == "acordao"


def test_relatorio_has_no_doc_type_guessed() -> None:
    row = _row("RELATÓRIO Trata-se de ação. É o relatório.")
    candidate = extract_candidate(row, "RELATÓRIO")
    assert "doc_type" not in candidate["info"]


_COMPOSITE_ACORDAO_TEXT = (
    "RELATÓRIO Trata-se de apelação cível. É o relatório. "
    "VOTO Presentes os pressupostos de admissibilidade, conheço do recurso. É como voto. "
    "EMENTA Direito civil. Recurso conhecido e provido. "
    "Vistos, relatados e discutidos estes autos, acordam os magistrados da 2ª Câmara "
    "Cível, na conformidade da ata de julgamentos, em NEGAR PROVIMENTO AO RECURSO, "
    "À UNANIMIDADE. Porto Velho, 1 de janeiro de 2024."
)


def test_internal_extraction_finds_acordao_decisorio_inside_composite_document() -> None:
    row = _row(_COMPOSITE_ACORDAO_TEXT)
    candidate = extract_internal_candidate(row, "acordao_decisorio")
    assert candidate is not None
    categories = [lab["category"] for lab in candidate["label"]]
    assert categories == ["acordao_decisorio_inicio", "acordao_decisorio_fim"]
    assert candidate["info"]["unmatched_pair"] is False
    assert candidate["info"]["extraction_mode"] == "internal"


def test_internal_extraction_offsets_are_exact_mid_document() -> None:
    row = _row(_COMPOSITE_ACORDAO_TEXT)
    candidate = extract_internal_candidate(row, "acordao_decisorio")
    for label in candidate["label"]:
        surface = candidate["text"][label["start"] : label["end"]]
        assert surface == surface.strip()
        assert surface != ""
    # the acordao_decisorio anchors must NOT be at the document boundaries
    # (that would mean this collapsed to the whole-document case, not a
    # genuine internal find).
    assert candidate["label"][0]["start"] > 0


def test_internal_extraction_matches_uppercase_closing() -> None:
    row = _row(
        "Vistos, relatados e discutidos estes autos, acordam os magistrados, "
        "em RECURSO PROVIDO, POR MAIORIA. Porto Velho."
    )
    candidate = extract_internal_candidate(row, "acordao_decisorio")
    assert candidate is not None
    fim = next(lab for lab in candidate["label"] if lab["category"] == "acordao_decisorio_fim")
    assert candidate["text"][fim["start"] : fim["end"]] == "POR MAIORIA."


def test_internal_extraction_no_inicio_match_is_rejected() -> None:
    row = _row("Texto qualquer sem nenhuma âncora de acordao_decisorio conhecida.")
    assert extract_internal_candidate(row, "acordao_decisorio") is None


def test_internal_extraction_missing_fim_is_unmatched_pair() -> None:
    row = _row(
        "Vistos, relatados e discutidos estes autos, acordam os magistrados "
        "da Câmara em julgar o recurso, sem uma fórmula de fechamento conhecida aqui."
    )
    candidate = extract_internal_candidate(row, "acordao_decisorio")
    assert candidate is not None
    categories = [lab["category"] for lab in candidate["label"]]
    assert categories == ["acordao_decisorio_inicio"]
    assert candidate["info"]["unmatched_pair"] is True


def test_internal_extraction_passes_final_invariants() -> None:
    row = _row(_COMPOSITE_ACORDAO_TEXT)
    candidate = extract_internal_candidate(row, "acordao_decisorio")
    assert check_final_invariants(candidate["text"], candidate["label"]) == []


def test_preliminar_numbered_heading_matches_and_finds_fim() -> None:
    row = _row(
        "É o relatório. VOTO 1. PRELIMINARES 1.1 Ilegitimidade passiva. O apelante alega "
        "sua ilegitimidade. Ante o exposto, rejeito a preliminar. Presentes os requisitos "
        "legais, conheço do apelo. 2. MÉRITO No mérito, ..."
    )
    candidate = extract_preliminar_candidate(row)
    assert candidate is not None
    categories = [lab["category"] for lab in candidate["label"]]
    assert categories == ["preliminar_inicio", "preliminar_fim"]
    assert candidate["info"]["unmatched_pair"] is False


def test_preliminar_statute_citation_digit_is_not_a_false_positive() -> None:
    """Regression for the real false positive found in a manual audit: a
    statute citation ending in "1998." (digit 8) followed by the
    dispositivo outcome word "PRELIMINARES." coincidentally matched a
    naive digit-period-PRELIMINAR pattern. Restricting the heading regex
    to a leading "1." specifically (preliminares is always the first
    numbered analysis section — 21/22 real documents, vs. this one false
    "8.") rejects it cleanly.
    """
    row = _row(
        "EMENTA CRIME AMBIENTAL. ART. 50 DA LEI N. 9.605/1998. PRELIMINARES. "
        "INÉPCIA DA PEÇA ACUSATÓRIA. AUSÊNCIA DE JUSTA CAUSA."
    )
    assert extract_preliminar_candidate(row) is None


def test_preliminar_no_heading_is_rejected() -> None:
    row = _row("Texto qualquer sem seção de preliminares numerada.")
    assert extract_preliminar_candidate(row) is None


def test_preliminar_missing_fim_is_unmatched_pair() -> None:
    row = _row(
        "VOTO 1. PRELIMINARES 1.1 Ilegitimidade passiva. Análise sem uma "
        "fórmula de fechamento reconhecida aqui."
    )
    candidate = extract_preliminar_candidate(row)
    assert candidate is not None
    categories = [lab["category"] for lab in candidate["label"]]
    assert categories == ["preliminar_inicio"]
    assert candidate["info"]["unmatched_pair"] is True


def test_preliminar_fim_without_trailing_period_still_matches() -> None:
    """The real closing sentence often continues past 'mérito' (e.g.
    '...passo a apreciar o mérito propriamente dito.') — the phrase bank
    entry has no trailing period so it matches regardless.
    """
    row = _row(
        "1. PRELIMINARES 1.1 Tempestividade. Presentes os requisitos de "
        "admissibilidade e os pressupostos processuais, passo a apreciar o mérito "
        "propriamente dito. 2. MÉRITO ..."
    )
    candidate = extract_preliminar_candidate(row)
    assert candidate is not None
    categories = [lab["category"] for lab in candidate["label"]]
    assert categories == ["preliminar_inicio", "preliminar_fim"]
    fim = candidate["label"][1]
    assert candidate["text"][fim["start"] : fim["end"]] == "passo a apreciar o mérito"


def test_preliminar_candidate_passes_final_invariants() -> None:
    row = _row(
        "1. PRELIMINARES 1.1 Tempestividade. Ante o exposto, rejeito a preliminar. 2. MÉRITO ..."
    )
    candidate = extract_preliminar_candidate(row)
    assert check_final_invariants(candidate["text"], candidate["label"]) == []
