"""Segmenter dataset lifecycle: candidate/document → annotation → review → release.

Implements RFC 0012 ("Segmentador v8: dataset confiável e baseline honesto
com dados reais", ``docs/rfc/0012-segmenter-dataset-confiavel-baseline.md``)
PR 1 — the artifact contract, splitter, and immutable release builder.
"""

from __future__ import annotations
