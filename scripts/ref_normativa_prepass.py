"""Regex pre-pass for ref_normativa spans.

ref_normativa dominates the v6 corpus (~65% of all spans), inflating macro-F1
and starving categories that actually need the model. Since ref_normativa is
well-served by regex, we handle it outside OPF and let the model focus on
context-dependent categories.

This module runs at inference BEFORE OPF. After OPF produces its spans, the
ref_normativa spans from this pre-pass are merged into the final output.

Usage:
    from scripts.ref_normativa_prepass import extract_ref_normativa
    spans = extract_ref_normativa(text)
"""

from __future__ import annotations

import re


REF_NORMATIVA_PATTERNS: list[str] = [
    r"[Aa]rt(?:igo)?\.?\s*\d+[º°ª]?(?:\s*,\s*[§IVXivx\d]+)*",
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
    """Merge OPF model spans with regex ref_normativa spans, removing overlaps."""
    all_spans = sorted(
        [*opf_spans, *ref_spans],
        key=lambda s: (s["start"], -s["end"]),
    )
    result: list[dict] = []
    last_end = -1
    for sp in all_spans:
        if sp["start"] >= last_end:
            result.append(sp)
            last_end = sp["end"]
    return result
