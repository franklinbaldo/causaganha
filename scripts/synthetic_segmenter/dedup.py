"""Duplicate and near-duplicate detection.

RFC 0011 §10, §15 — "hashes de texto normalizado; detecção de
quase-duplicatas". Two tiers, deliberately cheap (stdlib only, no
embedding model — this is a
Foundation-layer guard against accidental exact/near duplication across
splits or across repeated generation runs, not a semantic similarity
search):

- ``content_hash`` — exact-duplicate detection after normalizing
  whitespace/case, so two records differing only in incidental formatting
  still collide.
- ``near_duplicate_ratio`` — cheap edit-distance-based similarity
  (``difflib.SequenceMatcher``) for catching near-duplicates that a hash
  won't (e.g. a single mutated word). O(n*m) per pair — fine for auditing
  a batch against itself or against a small reference set; not intended
  for corpus-scale all-pairs comparison.
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
    """SHA-256 of the normalized text.

    Used to detect exact duplicates (RFC 0011 §15 ``content_sha256``)
    irrespective of incidental whitespace differences.
    """
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

    Still O(n^2) in the worst case — call on a batch (a single generation
    run), not the whole accumulated corpus; for corpus-scale dedup, blocking
    (MinHash/LSH, n-gram + length buckets) is a different, coarser
    algorithm, not a constant-factor speedup of this one. Returns
    (id_a, id_b, ratio) sorted by ratio descending.

    Length-based pruning: ``SequenceMatcher.ratio()`` is ``2*M/T`` where
    ``M`` (matching characters) can be at most ``min(len_a, len_b)`` and
    ``T = len_a + len_b`` — so ``2*min(len_a, len_b)/T`` is an EXACT upper
    bound on the ratio two texts of those lengths could ever achieve,
    regardless of content. A pair whose bound already falls below
    ``threshold`` cannot possibly reach it, so it's skipped without ever
    constructing a ``SequenceMatcher`` — this cannot produce a false
    negative (unlike an arbitrary "lengths within 10%" heuristic bucket,
    which could exclude a genuine near-duplicate pair sitting just outside
    the bucket), only prunes pairs that are mathematically impossible.
    """
    ids = list(records)
    normalized = {doc_id: normalize_text(text) for doc_id, text in records.items()}
    lengths = {doc_id: len(text) for doc_id, text in normalized.items()}
    out: list[tuple[str, str, float]] = []
    for i in range(len(ids)):
        id_a = ids[i]
        len_a = lengths[id_a]
        for j in range(i + 1, len(ids)):
            id_b = ids[j]
            len_b = lengths[id_b]
            total = len_a + len_b
            if total == 0:
                continue
            upper_bound = 2.0 * min(len_a, len_b) / total
            if upper_bound < threshold:
                continue
            ratio = SequenceMatcher(None, normalized[id_a], normalized[id_b]).ratio()
            if ratio >= threshold:
                out.append((id_a, id_b, ratio))
    return sorted(out, key=lambda t: t[2], reverse=True)
