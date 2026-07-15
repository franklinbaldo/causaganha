"""Anchor phrase variants per category.

RFC 0011 §5.2. Every phrase below is grounded in
``data/segmenter_splits/annotation_guideline_v7.md`` — the guideline's own
worked examples, not invented surface forms. ``corpus_stats.py`` (RFC 0011
§6.1) is the intended path for growing these lists from the real corpus
later; this module is the seed set a Phase-1 (no-LLM) generator needs to
run at all.

Two shapes, matching the guideline's two anchor schemes:

- ``SINGLE_ANCHOR_PHRASES[category]`` — a flat list of interchangeable
  surface forms for a single-anchor category.
- ``PAIR_PHRASES[base_name]`` — ``{"inicio": [...], "fim": [...]}`` for a
  start/end-pair category. The renderer looks up ``f"{base_name}_inicio"``/
  ``f"{base_name}_fim"`` against ``label_space.json`` — this module only
  knows the short human name.

``O`` and ``ref_normativa`` are deliberately absent: ``O`` isn't a
labeled span, and ``ref_normativa`` is excluded from the trainable v7
label space (RFC 0001) even though the guideline still documents it
conceptually.
"""

from __future__ import annotations


SINGLE_ANCHOR_PHRASES: dict[str, list[str]] = {
    "dispositivo_abertura": ["Ante o exposto", "Pelo exposto", "Posto isso", "Diante do exposto"],
    "fundamentacao_legal": [
        "nos termos do art. 932 do CPC",
        "conforme dispõe o art. 927 do CPC",
    ],
}

# resultado's surface form depends on the document's outcome (RFC 0011
# §3.1 DocumentSpec.outcome) — a different shape than the other
# single-anchor categories, so it gets its own lookup + accessor.
RESULTADO_PHRASES: dict[str, list[str]] = {
    "procedente": ["julgo procedente o pedido", "acolho os pedidos formulados"],
    "improcedente": ["julgo improcedentes os pedidos", "rejeito a pretensão inicial"],
    "parcialmente_provido": ["dou parcial provimento ao recurso"],
    "provido": ["dou provimento ao recurso"],
    "negado_provimento": ["nego provimento ao recurso", "conheço do recurso e lhe nego provimento"],
}

PAIR_PHRASES: dict[str, dict[str, list[str]]] = {
    "cabecalho": {
        "inicio": ["PODER JUDICIÁRIO"],
        "fim": ["Vistos."],
    },
    "ementa": {
        "inicio": ["EMENTA:", "EMENTA"],
        "fim": ["RELATÓRIO"],
    },
    "relatorio": {
        "inicio": ["RELATÓRIO", "Trata-se de"],
        "fim": ["É o relatório."],
    },
    "capitulo_merito": {
        "inicio": ["DO MÉRITO", "DECIDO", "Mérito:"],
        "fim": ["DISPOSITIVO"],
    },
    "preliminar": {
        "inicio": ["DAS PRELIMINARES", "PRELIMINAR"],
        "fim": ["Superada a preliminar, passo ao mérito."],
    },
    "honorarios": {
        "inicio": ["HONORÁRIOS:", "Dos honorários"],
        "fim": ["fixados na forma acima."],
    },
    "custas": {
        "inicio": ["CUSTAS:", "Das custas"],
        "fim": ["nos termos da lei."],
    },
    "encerramento": {
        "inicio": ["Publique-se.", "P.R.I."],
        "fim": ["Juiz de Direito"],
    },
    "voto": {
        "inicio": ["VOTO", "É como voto"],
        "fim": ["É o voto."],
    },
    "acordao_decisorio": {
        "inicio": ["ACORDAM os Desembargadores", "Vistos, relatados e discutidos"],
        "fim": ["à unanimidade.", "por maioria."],
    },
}


def resultado_phrase(outcome: str) -> str:
    """Return one canonical ``resultado`` surface form for ``outcome``.

    Deterministic (first entry) — callers wanting variation index into
    ``RESULTADO_PHRASES[outcome]`` themselves.
    """
    try:
        return RESULTADO_PHRASES[outcome][0]
    except KeyError:
        msg = f"no resultado phrase for outcome {outcome!r}"
        raise ValueError(msg) from None
