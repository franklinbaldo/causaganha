"""Robustness tests for the privacy-filter segmenter (``_segment``).

``_segment`` turns a judicial decision into character-level span labels that the
privacy-filter dataset / Colab notebook consume. The ``sec_dispositivo`` span in
particular is the supervision signal for the dispositivo NER model, so a few
invariants matter:

- no dispositivo anchor → ``None`` (the function's documented contract);
- the operative ruling is captured under ``sec_dispositivo``;
- structural sections are ordered and contiguous; and
- every emitted span stays within ``[0, len(text)]`` with ``start < end`` — an
  out-of-bounds or inverted span would crash the downstream char→token BIO
  alignment.
"""

from __future__ import annotations

from itertools import pairwise

from scripts.prepare_privacy_filter_dataset import _segment


# A compact but structurally complete decision: header, relatório, mérito,
# dispositivo, and a city+date signature block — enough to exercise every
# section boundary and a couple of entity patterns.
DECISION = """PODER JUDICIÁRIO DO ESTADO DE RONDÔNIA
Processo nº 0001234-56.2025.8.22.0001

Trata-se de ação de cobrança proposta por João da Silva.

Do mérito. Analiso o pedido conforme a Lei nº 8.078/90.

Ante o exposto, julgo procedente o pedido e condeno o réu ao pagamento.

Porto Velho, 15 de janeiro de 2025
Maria Santos
Juíza de Direito"""

_SECTION_LABELS = (
    "sec_cabecalho",
    "sec_relatorio",
    "sec_fundamentacao",
    "sec_dispositivo",
    "sec_assinatura",
)


def _span_text(text: str, span: list[int]) -> str:
    return text[span[0] : span[1]]


def test_returns_none_without_dispositivo_anchor() -> None:
    # No "ante o exposto"/"decido"/etc. anchor → cannot segment.
    assert _segment("Mero despacho de expediente, sem decisão de mérito.") is None


def test_dispositivo_section_captures_the_ruling() -> None:
    spans = _segment(DECISION)
    assert spans is not None
    assert "sec_dispositivo" in spans
    disp = _span_text(DECISION, spans["sec_dispositivo"][0])
    # The operative ruling — the exact text the dispositivo NER model must learn.
    assert "julgo procedente" in disp


def test_sections_are_ordered_and_contiguous() -> None:
    spans = _segment(DECISION)
    assert spans is not None

    present = [(lbl, spans[lbl][0]) for lbl in _SECTION_LABELS if lbl in spans]
    # At least the dispositivo + one neighbour should be detected here.
    assert any(lbl == "sec_dispositivo" for lbl, _ in present)

    # Each section starts exactly where the previous one ends (no gaps/overlap).
    for (_, prev), (_, nxt) in pairwise(present):
        assert prev[1] == nxt[0]


def test_all_spans_within_bounds_and_non_empty() -> None:
    spans = _segment(DECISION)
    assert spans is not None
    n = len(DECISION)
    for label, occurrences in spans.items():
        for span in occurrences:
            start, end = span
            assert 0 <= start < end <= n, f"{label} span {span} out of bounds (len={n})"


def test_collects_processo_cnj_entity() -> None:
    spans = _segment(DECISION)
    assert spans is not None
    assert "processo_cnj" in spans
    assert _span_text(DECISION, spans["processo_cnj"][0]) == "0001234-56.2025.8.22.0001"
