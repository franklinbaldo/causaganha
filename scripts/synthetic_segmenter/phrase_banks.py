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

``O`` is deliberately absent: it isn't a labeled span. ``ref_normativa``
is ALSO absent from ``SINGLE_ANCHOR_PHRASES``/``PAIR_PHRASES`` -- but,
unlike ``O``, it IS trained (added back to the v7 label space; see
``prepare_privacy_filter_dataset.py``'s comment above ``SPAN_CLASS_NAMES_V7``
for the full architecture rationale). It's absent from *this* module
specifically because it isn't an anchor-phrase category: real gold
sources it via a regex bootstrap (``scripts/ref_normativa_prepass.py``)
over already-written text, not a hand-picked surface form. The same
regex runs over synthetic filler text in ``renderer.py`` for parity --
``REF_NORMATIVA_FILLER_PHRASES`` below supplies citation-shaped sentence
fragments (including formats a real-corpus audit found the regex used to
truncate: thousands-separator article numbers, spelled-out inciso/
parágrafo/alínea) so the synthetic corpus doesn't quietly under-represent
the same formats the regex itself used to get wrong.
"""

from __future__ import annotations


SINGLE_ANCHOR_PHRASES: dict[str, list[str]] = {
    "dispositivo_abertura": ["Ante o exposto", "Pelo exposto", "Posto isso", "Diante do exposto"],
    "fundamentacao_legal": [
        "nos termos do art. 932 do CPC",
        "conforme dispõe o art. 927 do CPC",
        # Most frequent real-corpus shape (Round B audit, 2026-07-16): the
        # reasoning tie-in sits immediately adjacent to the operative verb,
        # as in the phrase below followed by JULGO PROCEDENTE -- every
        # subagent-confirmed fundamentacao_legal find followed this exact
        # "com fundamento no" pattern; every skipped candidate was a bare
        # citation elsewhere in the reasoning, not adjacent to the verb.
        "com fundamento no art. 487, I, do CPC",
    ],
}

# Legal-citation surface forms grounded in a real-corpus audit
# (scripts/ref_normativa_prepass.py's fix history) -- these are the exact
# formats a bare-\d+ / bare-char-class regex used to truncate before the
# fix (thousands-separator article numbers, spelled-out inciso/parágrafo/
# alínea). ``renderer.py`` splices these into filler prose so the same
# ``extract_ref_normativa`` regex that bootstraps real gold's
# ``ref_normativa`` spans finds an equally varied set in synthetic text --
# without this, the synthetic corpus would silently skew toward only the
# short "art. N do CPC" shape and under-represent the formats real
# citations actually take.
REF_NORMATIVA_FILLER_PHRASES: list[str] = [
    "nos termos do art. 1.000, do CPC",
    "com fulcro no art. 5º, inciso II, alínea b, do CPC",
    "nos termos do art. 927, parágrafo único, do CPC",
    "conforme o art. 924, II, do CPC",
    "na forma do art. 55 da Lei nº 9.099/95",
    "aplica-se a Súmula 331 do TST ao caso",
]

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
        # Confirmed against a real 22-document sample of numbered
        # "N. PRELIMINARES" sections inside composite ACÓRDÃO-tipo
        # documents (only phrases that actually fired are listed — several
        # other plausible-sounding candidates never matched a single real
        # document and were deliberately left out). "passo a apreciar o
        # mérito"/"passo a análise do mérito" are given WITHOUT a trailing
        # period: the real closing sentence continues past "mérito" in
        # most cases ("...mérito propriamente dito.", "...mérito, tem-se
        # que...") — same over-specification lesson as voto's fim.
        # "Preliminar acolhida."/"afasto a preliminar suscitada..." added
        # from the Round A audit (2026-07-16, 20 real acórdãos targeted
        # specifically for a numbered preliminar section): closings the
        # earlier 22-doc sample never happened to surface, but real enough
        # to appear twice independently across 20 documents.
        "fim": [
            "Superada a preliminar, passo ao mérito.",
            "Rejeitada a preliminar, passo ao exame do mérito.",
            "rejeito a preliminar.",
            "Rejeito a preliminar.",
            "não conheço da preliminar.",
            "passo a apreciar o mérito",
            "passo a análise do mérito",
            "Preliminar acolhida.",
            "afasto a preliminar suscitada, submetendo-a ao Colegiado.",
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
        # Uppercase variants confirmed against real ACÓRDÃO-tipo tjro_juris
        # documents: the dispositivo summary line is routinely rendered in
        # full caps ("...À UNANIMIDADE."), not just lowercase. The
        # ", NOS TERMOS DO VOTO DO RELATOR." variants are a second real
        # sentence-final pattern (comma, not period, after
        # UNANIMIDADE/MAIORIA) confirmed in a manual audit of internally-
        # extracted candidates — the shorter "À UNANIMIDADE."/"POR
        # MAIORIA." variants don't match this continuation.
        "fim": [
            "à unanimidade.",
            "por maioria.",
            "À UNANIMIDADE.",
            "POR MAIORIA.",
            "À UNANIMIDADE, NOS TERMOS DO VOTO DO RELATOR.",
            "POR MAIORIA, NOS TERMOS DO VOTO DO RELATOR.",
        ],
    },
}

# Real-corpus finding (Round B audit, 2026-07-16, 20 SENTENCA docs
# targeted for both "custas" and "honorarios" mentions): Juizado Especial
# sentencas overwhelmingly FUSE custas and honorários into one clause with
# no clean boundary between them ("Sem custas e sem honorários advocatícios
# nesta instância..."), not two independent clauses. That collision was
# severe enough to produce real BIOES overlap errors when independent
# subagents anchored both categories on the identical span. Each entry
# below is one fused sentence, pre-split into four non-overlapping
# fragments so ``renderer.py`` can emit ``custas_inicio``/``custas_fim``/
# ``honorarios_inicio``/``honorarios_fim`` from ONE shared clause -- the
# dominant real shape -- instead of two independently-generated ones.
FUSED_CUSTAS_HONORARIOS_TEMPLATES: list[dict[str, str]] = [
    {
        "custas_inicio": "Sem custas",
        "custas_fim": "processuais",
        "connector": " e sem ",
        "honorarios_inicio": "honorários",
        "honorarios_fim": "advocatícios nesta instância, nos termos do art. 55 da Lei nº 9.099/95.",
    },
    {
        "custas_inicio": "Isento de custas",
        "custas_fim": "iniciais adiadas e finais",
        "connector": " e de ",
        "honorarios_inicio": "honorários",
        "honorarios_fim": "advocatícios.",
    },
    {
        "custas_inicio": "Incabível condenação em custas",
        "custas_fim": "processuais",
        "connector": " e ",
        "honorarios_inicio": "honorários",
        "honorarios_fim": "advocatícios nesta instância, conforme artigo 55 da Lei 9.099/95.",
    },
]


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
