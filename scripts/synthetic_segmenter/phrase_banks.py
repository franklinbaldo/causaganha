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
    "procedente": [
        "julgo procedente o pedido",
        "acolho os pedidos formulados",
        "julgo procedente a pretensão inicial",
    ],
    "improcedente": [
        "julgo improcedentes os pedidos",
        "rejeito a pretensão inicial",
        "julgo improcedente o pedido",
    ],
    "parcialmente_provido": [
        "dou parcial provimento ao recurso",
        "dou provimento parcial ao apelo",
    ],
    "provido": [
        "dou provimento ao recurso",
        "dou provimento ao apelo",
    ],
    "negado_provimento": [
        "nego provimento ao recurso",
        "conheço do recurso e lhe nego provimento",
        "nego provimento ao apelo",
    ],
}

# Every list below carries at least two variants (RFC 0011 §5.2's own
# instruction not to invent surface forms still applies — these are all
# register-consistent paraphrases of the same guideline-documented cue,
# not new categories or new meanings). Single-entry lists were a Phase-1
# seed-set artifact, not a design choice: corpus_stats.py (§6.1) is still
# the intended long-run path for growing these from the real corpus.
PAIR_PHRASES: dict[str, dict[str, list[str]]] = {
    "cabecalho": {
        "inicio": ["PODER JUDICIÁRIO", "PODER JUDICIÁRIO DO ESTADO DE RONDÔNIA"],
        "fim": ["Vistos.", "Vistos, etc."],
    },
    "ementa": {
        "inicio": ["EMENTA:", "EMENTA"],
        "fim": ["RELATÓRIO", "RELATÓRIO."],
    },
    "relatorio": {
        "inicio": ["RELATÓRIO", "Trata-se de", "RELATÓRIO:"],
        # "dispensado...lei 9.099/95" variants are the Juizados Especiais/
        # Turmas Recursais convention (Lei 9.099/95 explicitly waives the
        # formal relatório) — confirmed against a real ~11k-document sample
        # of scripts/synthetic_segmenter's tjro_juris source corpus:
        # ~52% of real RELATÓRIO documents close this way, not with "É o
        # relatório." — a second real regime, not noise.
        "fim": [
            "É o relatório.",
            "É o breve relatório.",
            "É o sucinto relatório.",
            "dispensado o relatório na forma da lei 9.099/95.",
            "relatório dispensado nos termos da Lei nº 9.099/95.",
            "Relatório dispensado, nos termos da Lei n. 9.099/95.",
            "dispensado nos moldes do art. 38, LF nº 9.099/95, e Enunciado Cível FONAJE nº 92.",
        ],
    },
    "capitulo_merito": {
        "inicio": ["DO MÉRITO", "DECIDO", "Mérito:"],
        "fim": ["DISPOSITIVO", "DISPOSITIVO:"],
    },
    "preliminar": {
        "inicio": ["DAS PRELIMINARES", "PRELIMINAR"],
        "fim": [
            "Superada a preliminar, passo ao mérito.",
            "Rejeitada a preliminar, passo ao exame do mérito.",
        ],
    },
    "honorarios": {
        "inicio": ["HONORÁRIOS:", "Dos honorários"],
        "fim": ["fixados na forma acima.", "nos termos fixados."],
    },
    "custas": {
        "inicio": ["CUSTAS:", "Das custas"],
        "fim": ["nos termos da lei.", "na forma da lei processual."],
    },
    "encerramento": {
        "inicio": ["Publique-se.", "P.R.I."],
        "fim": ["Juiz de Direito", "Juiz de Direito.", "Desembargador(a) Relator(a)"],
    },
    "voto": {
        "inicio": ["VOTO", "É como voto"],
        # "...os autos à origem." is the Juizado Especial closing convention
        # (same real-corpus sample as relatorio's fim above) — deliberately
        # NOT including the lead-in clause ("transitada em julgado,"/"Após
        # o trânsito em julgado,"/"Com o trânsito em julgado"/"Oportunamente,"
        # all seen verbatim in the real sample): the lead-in varies freely,
        # only the closing "remetam-se/devolvam-se os autos à origem." is
        # stable, and RFC 0011 §5.2's own rule is short anchors (1-5 words).
        "fim": [
            "É o voto.",
            "É como voto.",
            "remetam-se os autos à origem.",
            "devolvam-se os autos à origem.",
        ],
    },
    "acordao_decisorio": {
        "inicio": ["ACORDAM os Desembargadores", "Vistos, relatados e discutidos"],
        "fim": ["à unanimidade.", "por maioria."],
    },
}


def resultado_phrase(outcome: str, *, variant: int = 0) -> str:
    """Return one ``resultado`` surface form for ``outcome``.

    ``variant`` indexes into ``RESULTADO_PHRASES[outcome]`` modulo its
    length — defaults to the first entry (backward compatible), callers
    wanting variation (e.g. ``renderer.py`` using ``spec.seed``) pass it
    explicitly.
    """
    try:
        variants = RESULTADO_PHRASES[outcome]
    except KeyError:
        msg = f"no resultado phrase for outcome {outcome!r}"
        raise ValueError(msg) from None
    return variants[variant % len(variants)]
