"""Anchor scrubbing for imported real excerpts (RFC 0011 §6.2 point 2).

A real excerpt pulled into a hybrid record (real fact/fundamentação
language, synthetic structure) may itself contain genuine anchor phrases —
"ante o exposto" inside a cited lower-court ruling, "É o relatório." from
a quoted passage. Left alone, those become **false negatives**: real
anchor surface forms sitting in the body text, never labeled, teaching the
model the opposite of what the anchor means.

RFC 0011 §6.2 requires every imported excerpt go through one of three
explicit outcomes for each occurrence found — never silently ignored:

- **discard** — reject the excerpt outright (caller picks a different one).
- **neutralize** — rewrite the occurrence into reported-speech framing (the
  same shape as the ``reported_prior_outcome``/``quoted_dispositivo`` hard
  negatives in ``hard_negatives.py``) so it no longer reads as an
  operative anchor.
- **promote_hard_negative** — leave the phrase exactly as-is and tell the
  caller to record it as a deliberate hard negative (RFC 0011 §5) rather
  than mutate it.

This module only ever touches **unlabeled** text — RFC 0011 §4.3's
pipeline order is "mutate unlabeled content, then insert labeled anchors,
then record offsets", so no edit-map (``transform.py``) bookkeeping is
needed here: there are no labels yet to preserve.
"""

from __future__ import annotations

import re

from scripts.synthetic_segmenter.phrase_banks import (
    PAIR_PHRASES,
    RESULTADO_PHRASES,
    SINGLE_ANCHOR_PHRASES,
)


class ExcerptContainsAnchorError(ValueError):
    """Raised by ``scrub_excerpt(mode="discard")`` when an anchor is found."""


def _all_known_phrases() -> dict[str, str]:
    """Return ``{surface_phrase: category}`` for every phrase-bank entry.

    Longest surface forms first isn't handled here — callers doing
    positional scrubbing should sort matches by span, not by this dict's
    iteration order.
    """
    phrases: dict[str, str] = {}
    for category, variants in SINGLE_ANCHOR_PHRASES.items():
        for variant in variants:
            phrases[variant] = category
    for variants in RESULTADO_PHRASES.values():
        for variant in variants:
            phrases[variant] = "resultado"
    for base, by_suffix in PAIR_PHRASES.items():
        for suffix, variants in by_suffix.items():
            for variant in variants:
                phrases[variant] = f"{base}_{suffix}"
    return phrases


def find_anchor_occurrences(text: str) -> list[dict]:
    """Return every phrase-bank anchor occurring verbatim in ``text``.

    Each result is ``{"category": str, "start": int, "end": int, "surface": str}``,
    sorted by ``start``. Overlapping matches (one phrase is a substring of
    another) are all reported — callers resolve overlap when acting on the
    list, this function only detects.
    """
    occurrences: list[dict] = []
    for surface, category in _all_known_phrases().items():
        pattern = re.escape(surface)
        occurrences.extend(
            {
                "category": category,
                "start": match.start(),
                "end": match.end(),
                "surface": surface,
            }
            for match in re.finditer(pattern, text)
        )
    return sorted(occurrences, key=lambda occ: (occ["start"], occ["end"]))


def _drop_nested(occurrences: list[dict]) -> list[dict]:
    """Keep only non-overlapping occurrences, preferring the longest match at each start."""
    kept: list[dict] = []
    prev_end = -1
    for occ in sorted(occurrences, key=lambda o: (o["start"], -(o["end"] - o["start"]))):
        if occ["start"] >= prev_end:
            kept.append(occ)
            prev_end = occ["end"]
    return sorted(kept, key=lambda o: o["start"])


_WRAP_PREFIX = 'o excerto registra que "'
_WRAP_SUFFIX = '"'


def _already_wrapped(text: str, occ: dict) -> bool:
    """True if ``occ`` is already framed by a prior ``neutralize_excerpt`` pass."""
    before = text[max(0, occ["start"] - len(_WRAP_PREFIX)) : occ["start"]]
    after = text[occ["end"] : occ["end"] + len(_WRAP_SUFFIX)]
    return before == _WRAP_PREFIX and after == _WRAP_SUFFIX


def neutralize_excerpt(text: str) -> str:
    """Rewrite every anchor occurrence into quoted reported-speech framing.

    Matches the shape of the ``quoted_dispositivo``/``reported_prior_outcome``
    hard negatives: an anchor phrase quoted inside an attribution reads as
    non-operative, not as the section's own operative anchor. Idempotent —
    an occurrence already sitting inside a prior pass's wrapper is left
    alone rather than re-wrapped.
    """
    candidates = _drop_nested(find_anchor_occurrences(text))
    occurrences = [occ for occ in candidates if not _already_wrapped(text, occ)]
    if not occurrences:
        return text

    parts: list[str] = []
    cursor = 0
    for occ in occurrences:
        parts.append(text[cursor : occ["start"]])
        parts.append(f"{_WRAP_PREFIX}{occ['surface']}{_WRAP_SUFFIX}")
        cursor = occ["end"]
    parts.append(text[cursor:])
    return "".join(parts)


def scrub_excerpt(text: str, *, mode: str = "neutralize") -> str:
    """Apply one of the three RFC 0011 §6.2 outcomes to anchors found in ``text``.

    ``mode``:

    - ``"neutralize"`` (default) — rewrite occurrences via
      :func:`neutralize_excerpt`.
    - ``"discard"`` — raise :class:`ExcerptContainsAnchorError` if any
      occurrence is found; return ``text`` unchanged otherwise.
    - ``"promote_hard_negative"`` — return ``text`` unchanged; the caller
      is responsible for recording ``hard_negative_families`` provenance
      (RFC 0011 §5) rather than treating the excerpt as anchor-free.
    """
    occurrences = find_anchor_occurrences(text)
    if mode == "neutralize":
        return neutralize_excerpt(text)
    if mode == "discard":
        if occurrences:
            categories = sorted({occ["category"] for occ in occurrences})
            msg = f"excerpt contains {len(occurrences)} anchor occurrence(s) of {categories}"
            raise ExcerptContainsAnchorError(msg)
        return text
    if mode == "promote_hard_negative":
        return text
    msg = f"unknown scrub mode {mode!r}, expected 'neutralize'/'discard'/'promote_hard_negative'"
    raise ValueError(msg)
