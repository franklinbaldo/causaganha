"""Tests for scripts.juris_extract_gold_candidates."""

from __future__ import annotations

from scripts.juris_extract_gold_candidates import extract_candidate
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
