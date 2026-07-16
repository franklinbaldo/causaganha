"""Regex pre-pass for ref_normativa spans.

ref_normativa dominates the v6 corpus (~65% of all spans) and is a highly
regular pattern (article/law/súmula citations) — well-served by regex.
This module has two roles, not one:

1. **Inference-time complement**: runs at inference BEFORE OPF; after OPF
   produces its spans, the spans from this pre-pass are merged into the
   final output (``merge_with_opf_spans``), preferring the model's span
   on any overlap.
2. **Training-label bootstrap**: OPF is ALSO trained on ref_normativa
   (added back to ``SPAN_CLASS_NAMES_V7`` — a deployed model should
   identify every category standalone, not depend on a runtime regex
   correctly handling every real-world citation format). This module's
   output is the same regex used to bootstrap those training labels
   against real corpus text — high-precision enough to trust directly,
   same as any other regex-derived weak-supervision source.

Usage:
    from scripts.ref_normativa_prepass import extract_ref_normativa
    spans = extract_ref_normativa(text)
"""

from __future__ import annotations

import re


# Modifiers that can trail an article number, joined by commas — inciso/
# parágrafo/alínea, spelled out or abbreviated. Built (and fixed) against
# real TJRO citation text, not designed in the abstract:
#
# - A bare `[§IVXivx\d]+` char-class continuation (the original design)
#   silently truncates spelled-out words: "inciso" starts with the
#   letter "i", which IS in that class, so it matches just "i" and stops
#   — "art. 5º, inciso II, alínea b" was collapsing to "art. 5º, i".
#   Confirmed as a real, common truncation (not a hypothetical edge
#   case) via manual audit of real TJRO SENTENÇA text.
# - `\b[IVXLCDM]+\b` (word-bounded) is kept alongside the spelled-out
#   "incisos? ..." form because Brazilian legal writing commonly drops
#   the word entirely ("art. 924, II" meaning "art. 924, inciso II") —
#   removing it would be its own regression, not a fix.
_ARTICLE_MODIFIER = (
    r"§\s*\d+[º°ª]?"
    r"|par[áa]grafo\s+(?:[úu]nico|primeiro|segundo|terceiro|quarto|quinto|\d+[º°ª]?)"
    r"|incisos?\s+[IVXLCDM]+(?:\s*(?:,|e)\s*[IVXLCDM]+)*"
    r"|al[íi]neas?\s+[\"'“]?[a-zA-Z][\"'”]?"
    r"|\b[IVXLCDM]+\b"
)

REF_NORMATIVA_PATTERNS: list[str] = [
    # \d{1,3}(?:\.\d{3})* (not bare \d+): article numbers above 999 use a
    # thousands-separator period ("art. 1.000", "art. 1.037" — CPC/2015 has
    # 1072 articles). A bare \d+ stops at the period, truncating the real
    # citation to "art. 1" — confirmed as a real, non-rare bug (~5% of
    # "art."-citations in a real TJRO sample) via manual audit before this
    # fix, not a hypothetical edge case.
    r"[Aa]rt(?:igo)?\.?\s*\d{1,3}(?:\.\d{3})*[º°ª]?(?:\s*,\s*(?:" + _ARTICLE_MODIFIER + r"))*",
    r"[Ll]ei\s+(?:[Cc]omplementar\s+)?(?:[Nn](?:[ºo°.])\s*)?[\d.]+(?:/\d{2,4})?",
    r"[Ss][úu]mula\s+(?:[Vv]inculante\s+)?\d+",
    r"[Tt]ema\s+\d+",
    r"[Dd]ecreto(?:-[Ll]ei)?\s+(?:[Nn](?:[ºo°.])\s*)?[\d.]+(?:/\d{2,4})?",
    r"\b(?:CPC|CC|CDC|CLT|CF|CTN|CP|CPP|ECA|LRF|LINDB)\b",
]

_REF_NORMATIVA_RE = re.compile("|".join(REF_NORMATIVA_PATTERNS))


def extract_ref_normativa(text: str) -> list[dict]:
    """Extract ref_normativa spans from text using regex."""
    spans: list[dict] = []
    for m in _REF_NORMATIVA_RE.finditer(text):
        s, e = m.start(), m.end()
        surface = text[s:e].strip()
        if not surface:
            continue
        spans.append({"category": "ref_normativa", "start": s, "end": e})
    return spans


def merge_with_opf_spans(
    opf_spans: list[dict],
    ref_spans: list[dict],
) -> list[dict]:
    """Merge OPF model spans with regex ref_normativa spans, removing overlaps.

    ``opf_spans`` (the model's or gold's own labels) always win — a
    ``ref_spans`` entry is only kept if it overlaps NONE of them.

    Real bug fixed here: the original implementation sorted both lists
    together by ``(start, -end)`` and scanned greedily, which only
    prioritizes ``opf_spans`` on an EXACT start-position tie. A regex span
    that starts earlier than a real gold label but partially overlaps it
    (e.g. a "custas_fim" anchor ending inside a "Lei n. 9.099/95" citation
    the regex also matches) sorted first and silently displaced the gold
    label — confirmed as a real occurrence, not a hypothetical, when
    ref_normativa was added back to the trained label space and a real
    gold document's own custas_fim span was dropped by this exact case.
    """
    result = sorted(opf_spans, key=lambda s: s["start"])
    occupied = [(s["start"], s["end"]) for s in result]
    for sp in sorted(ref_spans, key=lambda s: s["start"]):
        if not any(sp["start"] < e and s < sp["end"] for s, e in occupied):
            result.append(sp)
            occupied.append((sp["start"], sp["end"]))
    return sorted(result, key=lambda s: s["start"])
