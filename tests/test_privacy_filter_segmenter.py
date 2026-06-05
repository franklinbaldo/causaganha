"""Tests for the anchor-span segmenter (v7 ontology).

``segment()`` finds short anchor cues in judicial decisions.
v7 has two anchor schemes: single-anchor (6 categories) and start/end
pairs (9x2=18 categories) for a total of 24 + O = 25 entries.

The bootstrap ``segment()`` only emits v6-era single-anchor categories;
v7 paired categories are produced by subagent annotation, not regex.

Returns a list of ``{"category": str, "start": int, "end": int}`` dicts in OPF
format, or None if no dispositivo opening cue is found.
"""

from __future__ import annotations

from scripts.prepare_privacy_filter_dataset import (
    SPAN_CLASS_NAMES_V7,
    _stratified_split,
    segment,
)


DECISION = """PODER JUDICIÁRIO DO ESTADO DE RONDÔNIA
Processo nº 0001234-56.2025.8.22.0001

Trata-se de ação de cobrança proposta por João da Silva, conforme art. 927 do CPC.

Do mérito. Analiso o pedido conforme a Lei nº 8.078/90.

Ante o exposto, julgo procedente o pedido e condeno o réu ao pagamento de R$ 5.000,00.

Porto Velho, 15 de janeiro de 2025
Maria Santos
Juíza de Direito"""


def _spans_by_category(spans: list[dict]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for sp in spans:
        result.setdefault(sp["category"], []).append(sp)
    return result


def _span_text(text: str, span: dict) -> str:
    return text[span["start"] : span["end"]]


def test_returns_none_without_dispositivo_anchor() -> None:
    assert segment("Mero despacho de expediente, sem decisão de mérito.") is None


def test_finds_dispositivo_abertura() -> None:
    spans = segment(DECISION)
    assert spans is not None
    by_cat = _spans_by_category(spans)
    assert "dispositivo_abertura" in by_cat
    surface = _span_text(DECISION, by_cat["dispositivo_abertura"][0])
    assert "Ante o exposto" in surface


def test_finds_resultado() -> None:
    spans = segment(DECISION)
    assert spans is not None
    by_cat = _spans_by_category(spans)
    assert "resultado" in by_cat
    surface = _span_text(DECISION, by_cat["resultado"][0])
    assert "julgo procedente" in surface


def test_finds_ref_processual() -> None:
    spans = segment(DECISION)
    assert spans is not None
    by_cat = _spans_by_category(spans)
    assert "ref_processual" in by_cat
    surface = _span_text(DECISION, by_cat["ref_processual"][0])
    assert "0001234-56.2025.8.22.0001" in surface


def test_finds_valor_condenacao() -> None:
    spans = segment(DECISION)
    assert spans is not None
    by_cat = _spans_by_category(spans)
    assert "valor_condenacao" in by_cat
    surface = _span_text(DECISION, by_cat["valor_condenacao"][0])
    assert "5.000,00" in surface


def test_finds_ref_normativa() -> None:
    spans = segment(DECISION)
    assert spans is not None
    by_cat = _spans_by_category(spans)
    assert "ref_normativa" in by_cat
    surfaces = [_span_text(DECISION, sp) for sp in by_cat["ref_normativa"]]
    assert any("art." in s.lower() or "lei" in s.lower() for s in surfaces)


def test_all_spans_within_bounds_and_non_empty() -> None:
    spans = segment(DECISION)
    assert spans is not None
    n = len(DECISION)
    for sp in spans:
        assert 0 <= sp["start"] < sp["end"] <= n, (
            f"{sp['category']} span [{sp['start']}:{sp['end']}] out of bounds (len={n})"
        )


def test_no_overlapping_spans() -> None:
    spans = segment(DECISION)
    assert spans is not None
    sorted_spans = sorted(spans, key=lambda s: (s["start"], -s["end"]))
    for i in range(len(sorted_spans) - 1):
        assert sorted_spans[i]["end"] <= sorted_spans[i + 1]["start"], (
            f"Overlapping: {sorted_spans[i]} and {sorted_spans[i + 1]}"
        )


def test_spans_have_correct_format() -> None:
    spans = segment(DECISION)
    assert spans is not None
    valid_cats = set(SPAN_CLASS_NAMES_V7) - {"O"}
    for sp in spans:
        assert set(sp.keys()) == {"category", "start", "end"}
        assert sp["category"] in valid_cats
        assert isinstance(sp["start"], int)
        assert isinstance(sp["end"], int)


def test_v7_label_space_has_25_entries() -> None:
    assert len(SPAN_CLASS_NAMES_V7) == 25
    assert SPAN_CLASS_NAMES_V7[0] == "O"
    assert "dispositivo_abertura" in SPAN_CLASS_NAMES_V7
    assert "ementa_inicio" in SPAN_CLASS_NAMES_V7
    assert "ementa_fim" in SPAN_CLASS_NAMES_V7
    assert "encerramento_inicio" in SPAN_CLASS_NAMES_V7
    assert "encerramento_fim" in SPAN_CLASS_NAMES_V7
    assert "fundamentacao_legal" in SPAN_CLASS_NAMES_V7


def test_stratified_split_preserves_categories() -> None:
    records = [
        {"text": f"text_{i}", "label": [{"category": cat, "start": 0, "end": 5}]}
        for i, cat in enumerate(
            ["dispositivo_abertura"] * 10 + ["resultado"] * 10 + ["ref_normativa"] * 10
        )
    ]
    splits = _stratified_split(records, seed=42)
    assert set(splits.keys()) == {"train", "val", "test"}
    assert len(splits["train"]) + len(splits["val"]) + len(splits["test"]) == 30
    for split_name, split_data in splits.items():
        cats = {rec["label"][0]["category"] for rec in split_data}
        if len(split_data) >= 3:
            assert len(cats) > 1, f"{split_name} has only one category: {cats}"
