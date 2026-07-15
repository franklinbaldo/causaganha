"""Synthetic/augmented training data infrastructure for the decision segmenter.

Foundation layer (RFC 0011, docs/rfc/0011-gerador-sintetico-segmentador.md):
correctness infrastructure shared by every later generation/augmentation
module — the transformation contract (transform.py), source-family split
enforcement (split_guard.py), the provenance schema (provenance.py), and
duplicate detection (dedup.py). Nothing in this package generates training
data yet; it exists so that whatever generates it later cannot silently
corrupt offsets or leak across train/val/test.
"""

from __future__ import annotations
