"""Duplicate and near-duplicate detection (RFC 0012 §10).

Two tiers, deliberately cheap (stdlib only, no embedding model) — a guard
against exact/near duplication across splits, not a semantic similarity
search:

- ``content_hash`` — exact-duplicate detection after normalizing
  whitespace/case, so two records differing only in incidental formatting
  still collide.
- ``near_duplicate_ratio`` — cheap edit-distance-based similarity
  (``difflib.SequenceMatcher``) for catching near-duplicates a hash won't
  (e.g. a single mutated word). O(n*m) per pair, so calling it directly for
  every pair of a corpus is still expensive; ``find_near_duplicates`` prunes
  pairs a length bound proves can't reach ``threshold`` before calling it,
  which is what makes corpus-scale all-pairs use (e.g.
  ``segmenter_dataset.splits.build_groups``) practical.

Reused near-verbatim from PR #832's ``scripts/synthetic_segmenter/dedup.py``
(RFC 0012 §18 — this was already generically correct, no synthetic-specific
assumptions to strip out).
"""

from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Collapse whitespace and lowercase — for hashing/comparison only.

    Never for the actual training text (which must preserve original
    formatting for offset correctness).
    """
    return _WHITESPACE_RE.sub(" ", text).strip().lower()


def content_hash(text: str) -> str:
    """SHA-256 of the normalized text — RFC 0012 §10 exact-duplicate detection."""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def near_duplicate_ratio(text_a: str, text_b: str) -> float:
    """SequenceMatcher ratio in [0, 1] on normalized text; 1.0 = identical."""
    return SequenceMatcher(None, normalize_text(text_a), normalize_text(text_b)).ratio()


def find_exact_duplicates(records: dict[str, str]) -> list[tuple[str, str]]:
    """``records`` maps id -> text. Returns pairs of ids sharing a content_hash."""
    by_hash: dict[str, list[str]] = {}
    for doc_id, text in records.items():
        by_hash.setdefault(content_hash(text), []).append(doc_id)
    return [
        (ids[i], ids[j])
        for ids in by_hash.values()
        if len(ids) > 1
        for i in range(len(ids))
        for j in range(i + 1, len(ids))
    ]


def find_near_duplicates(
    records: dict[str, str], threshold: float = 0.9
) -> list[tuple[str, str, float]]:
    """All-pairs near-duplicate search above ``threshold``.

    ``SequenceMatcher.ratio() == 2*M/T`` where ``T = len(a) + len(b)`` and
    ``M <= min(len(a), len(b))`` — so a pair can only reach ``threshold`` if
    ``2*min(la, lb) >= threshold*(la+lb)``. This is a provable upper bound
    (not a heuristic), so sorting by length and skipping pairs outside that
    band drops zero true near-duplicates while pruning most of the O(n^2)
    candidates before touching ``SequenceMatcher`` at all — corpus-scale use
    (``segmenter_dataset.splits.build_groups`` over the whole accumulated
    store, not just one batch) made the unpruned scan take minutes once the
    corpus passed ~150 documents. ``quick_ratio()`` (itself a cheap,
    guaranteed upper bound on ``ratio()``) prunes further before the actual
    edit-distance computation. Returns ``(id_a, id_b, ratio)`` sorted by
    ratio descending, ties broken by original insertion order (matching a
    naive nested-loop scan over ``records``).

    The bound is checked as ``2*la >= threshold*(la+lb)`` rather than via a
    precomputed ``max_length_b = la*(2-threshold)/threshold`` compared with
    ``lb`` — the division form can round the wrong way at an exact boundary
    (e.g. threshold 0.8 with lengths 2 and 3: ``2*(2-0.8)/0.8`` evaluates to
    ``2.9999999999999996``, silently excluding a pair whose true ratio is
    exactly ``0.8``) and requires excluding ``length_a == 0`` / non-positive
    ``threshold`` as special cases even though both are legal inputs (two
    empty-after-normalization texts are identical, ratio 1.0; threshold 0 is
    accepted by ``SplitManifest._validate_ratios`` and must union every
    pair, since every ratio is >= 0).
    """
    normalized = {doc_id: normalize_text(text) for doc_id, text in records.items()}
    # `SequenceMatcher(None, a, b).ratio()` is not guaranteed symmetric (its
    # matching-block search is driven by junk/popularity stats built from
    # `b` alone) — comparing candidates in length-sorted order would silently
    # swap which side is `a` vs `b` relative to a naive scan, changing some
    # ratios. Keep insertion order for the actual comparison so results are
    # identical to comparing every pair in `records`' own order; length-sort
    # is only used to bound the *candidate* search.
    insertion_index = {doc_id: index for index, doc_id in enumerate(records)}
    order = sorted(normalized, key=lambda doc_id: len(normalized[doc_id]))
    lengths = [len(normalized[doc_id]) for doc_id in order]
    n = len(order)

    out: list[tuple[str, str, float]] = []
    for i in range(n):
        length_a = lengths[i]
        j = i + 1
        while j < n and 2 * length_a >= threshold * (length_a + lengths[j]):
            left, right = order[i], order[j]
            id_a, id_b = (
                (left, right) if insertion_index[left] < insertion_index[right] else (right, left)
            )
            matcher = SequenceMatcher(None, normalized[id_a], normalized[id_b])
            if matcher.quick_ratio() >= threshold:
                ratio = matcher.ratio()
                if ratio >= threshold:
                    out.append((id_a, id_b, ratio))
            j += 1
    out.sort(key=lambda t: (insertion_index[t[0]], insertion_index[t[1]]))
    out.sort(key=lambda t: t[2], reverse=True)
    return out
