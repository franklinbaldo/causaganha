"""Duplicate and near-duplicate detection (RFC 0012 §10).

Two tiers, deliberately cheap (stdlib only, no embedding model) — a guard
against exact/near duplication across splits, not a semantic similarity
search:

- ``content_hash`` — exact-duplicate detection after normalizing
  whitespace/case, so two records differing only in incidental formatting
  still collide.
- ``near_duplicate_ratio`` — cheap edit-distance-based similarity
  (``difflib.SequenceMatcher``) for catching near-duplicates a hash won't
  (e.g. a single mutated word). O(n*m) per pair — fine for auditing a batch
  against itself or against a small reference set; not intended for
  corpus-scale all-pairs comparison.

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

    O(n^2) — call on a batch, not the whole accumulated corpus. Returns
    ``(id_a, id_b, ratio)`` sorted by ratio descending.
    """
    ids = list(records)
    out: list[tuple[str, str, float]] = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            ratio = near_duplicate_ratio(records[ids[i]], records[ids[j]])
            if ratio >= threshold:
                out.append((ids[i], ids[j], ratio))
    return sorted(out, key=lambda t: t[2], reverse=True)
