"""Phase 1-bis: mechanical augmentation of real training gold (RFC 0011 §14).

Regex-driven variation of an already-labeled real training record —
capitalization, whitespace/line-break noise, and curated synonym
substitution — routed through ``transform.apply_edits`` so every output
record keeps ``text[start:end] == expected_surface`` for every label.

RFC 0011 §11.2's mutation classification is the design constraint, not a
post-hoc check:

- **Outside labeled spans**: broadly permitted (whitespace, case noise).
- **Inside labeled spans**: only via a **category allowlist of recognized
  variants** — in practice, the surface must already match a known
  ``phrase_banks.py`` entry, and the substitution swaps in a different
  entry from the *same* category (and, for ``resultado``, the same
  outcome — ``procedente``/``improcedente`` are legally opposite, never
  interchangeable). A label whose surface isn't a recognized variant is
  left untouched rather than guessed at.
- **Anchor-destroying transforms** (turning a label into a hard negative)
  are out of scope here — RFC 0011 §11.2(c) allows them only when the
  label is deliberately removed and the result stays coherent; that's a
  hard-negative-generation concern (``hard_negatives.py``), not mechanical
  augmentation of gold.

Split safety is the caller's responsibility (same pattern as
``corpus_stats.py``): this module augments whatever record it's given: it
never look up or enforce which split ``info["doc_id"]`` belongs to. Callers
must only pass train-split records (RFC 0011 §10) — see
``split_guard.require_train_only_sources``.
"""

from __future__ import annotations

import random
import re

from scripts.synthetic_segmenter.phrase_banks import (
    PAIR_PHRASES,
    RESULTADO_PHRASES,
    SINGLE_ANCHOR_PHRASES,
)
from scripts.synthetic_segmenter.provenance import default_provenance
from scripts.synthetic_segmenter.transform import Edit, apply_edits


AUGMENTATION_FAMILIES = ("whitespace", "case", "synonym")

_WHITESPACE_RUN_RE = re.compile(r"[ ]{1,}")
_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]{3,}")

_WHITESPACE_VARIANTS = (" ", "  ", "\n")


def _label_ranges(labels: list[dict]) -> list[tuple[int, int]]:
    return [(label["start"], label["end"]) for label in labels]


def _is_outside_all(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return all(end <= r_start or start >= r_end for r_start, r_end in ranges)


def _accept_nonoverlapping(candidates: list[Edit]) -> list[Edit]:
    """Keep candidates in start order, dropping any that overlaps an already-kept one."""
    accepted: list[Edit] = []
    prev_end = -1
    for edit in sorted(candidates, key=lambda e: e.start):
        if edit.start >= prev_end:
            accepted.append(edit)
            prev_end = edit.end
    return accepted


def whitespace_noise_edits(text: str, labels: list[dict], *, rng: random.Random) -> list[Edit]:
    """Vary single-space runs outside every labeled span (RFC 0011 §11.2 "outside")."""
    ranges = _label_ranges(labels)
    edits: list[Edit] = []
    for match in _WHITESPACE_RUN_RE.finditer(text):
        start, end = match.start(), match.end()
        if not _is_outside_all(start, end, ranges):
            continue
        replacement = rng.choice(_WHITESPACE_VARIANTS)
        if replacement == match.group(0):
            continue
        edits.append(Edit(start=start, end=end, replacement=replacement, reason="whitespace_noise"))
    return edits


def case_noise_edits(
    text: str, labels: list[dict], *, rng: random.Random, probability: float = 0.15
) -> list[Edit]:
    """Randomly upper/lowercase whole words outside every labeled span."""
    ranges = _label_ranges(labels)
    edits: list[Edit] = []
    for match in _WORD_RE.finditer(text):
        start, end = match.start(), match.end()
        if not _is_outside_all(start, end, ranges):
            continue
        if rng.random() >= probability:
            continue
        word = match.group(0)
        replacement = word.upper() if rng.random() < 0.5 else word.lower()
        if replacement == word:
            continue
        edits.append(Edit(start=start, end=end, replacement=replacement, reason="case_noise"))
    return edits


def _pair_base_and_suffix(category: str) -> tuple[str, str] | None:
    for suffix in ("_inicio", "_fim"):
        if category.endswith(suffix):
            base = category[: -len(suffix)]
            if base in PAIR_PHRASES:
                return base, suffix.lstrip("_")
    return None


def _allowlisted_variant(category: str, surface: str, *, rng: random.Random) -> str | None:
    """Return a different, same-meaning surface form for ``surface``, or None if not eligible.

    Only fires when ``surface`` already matches a recognized phrase-bank
    variant for ``category`` — RFC 0011 §11.2's allowlist rule.
    """
    if category in SINGLE_ANCHOR_PHRASES:
        variants = SINGLE_ANCHOR_PHRASES[category]
        if surface in variants:
            others = [v for v in variants if v != surface]
            return rng.choice(others) if others else None
        return None

    if category == "resultado":
        for variants in RESULTADO_PHRASES.values():
            if surface in variants:
                others = [v for v in variants if v != surface]
                return rng.choice(others) if others else None
        return None

    pair = _pair_base_and_suffix(category)
    if pair is not None:
        base, suffix = pair
        variants = PAIR_PHRASES[base][suffix]
        if surface in variants:
            others = [v for v in variants if v != surface]
            return rng.choice(others) if others else None
        return None

    return None


def synonym_substitution_edits(text: str, labels: list[dict], *, rng: random.Random) -> list[Edit]:
    """Swap a label's surface for a different allowlisted variant of the same category."""
    edits: list[Edit] = []
    for label in labels:
        surface = text[label["start"] : label["end"]]
        replacement = _allowlisted_variant(label["category"], surface, rng=rng)
        if replacement is None:
            continue
        edits.append(
            Edit(
                start=label["start"],
                end=label["end"],
                replacement=replacement,
                reason="synonym_substitution",
            )
        )
    return edits


def augment_record(
    record: dict,
    *,
    seed: int,
    families: tuple[str, ...] = AUGMENTATION_FAMILIES,
) -> dict:
    """Augment one real gold ``{"text", "label", "info"}`` record.

    Returns a new record with ``info.source_type = "augmented_real"``
    (RFC 0011 §15) pointing back at the parent via ``source_doc_ids``.
    Deterministic in ``seed`` — same input + seed always yields the same
    output.
    """
    text = record["text"]
    labels = record["label"]
    parent_id = record["info"]["doc_id"]

    rng = random.Random(seed)
    candidates: list[Edit] = []
    if "synonym" in families:
        candidates.extend(synonym_substitution_edits(text, labels, rng=rng))
    if "whitespace" in families:
        candidates.extend(whitespace_noise_edits(text, labels, rng=rng))
    if "case" in families:
        candidates.extend(case_noise_edits(text, labels, rng=rng))

    edits = _accept_nonoverlapping(candidates)
    result = apply_edits(text, labels, edits)

    info = default_provenance("augmented_real")
    info["source_doc_ids"] = [parent_id]
    info["augmentation_seed"] = seed
    info["augmentation_families"] = list(families)
    return {"text": result.text, "label": result.labels, "info": info}
