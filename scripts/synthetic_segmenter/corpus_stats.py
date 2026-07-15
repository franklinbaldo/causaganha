"""Aggregate calibration from the real corpus (RFC 0011 §6.1).

Computes structural statistics — document length distribution, section
presence rate — from a ``textos`` table (schema: ``id``, ``texto``, per
``src/causaganha/consolidate/schema_registry.py``), so ``DocumentSpec``
sampling and ``phrase_banks.py`` are calibrated against what the real
corpus actually looks like, not invented frequencies.

Takes an already-connected ``ibis.Table`` rather than doing I/O itself —
callers build it via ``con.read_parquet(...)`` (production, matching
``scripts/pipeline/embed_v2.py``'s existing pattern) or
``ibis.memtable(...)`` (tests, no file/network needed).

**Split safety is the caller's responsibility, by design.** This module
never sees which documents are val/test — callers must pass an
already-train-only table (RFC 0011 §10 ``split_guard.calibration_eligible_ids``
filters the id set; the caller applies that filter, e.g. via
``table.filter(table.id.isin(eligible_ids))``, before it ever reaches this
module). Keeping that filtering out of this module is deliberate: it
can't leak val/test into calibration if it never receives val/test rows
to begin with.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.synthetic_segmenter.phrase_banks import PAIR_PHRASES


if TYPE_CHECKING:
    import ibis


def compute_structural_stats(table: ibis.Table) -> dict:
    """Return length distribution + per-section presence rate over ``table``.

    ``table`` must already be filtered to train-only documents (see module
    docstring). Presence rate is a cheap keyword heuristic — counts a
    section as "present" if any of its known ``_inicio`` phrase-bank
    variants appears as a literal substring, which undercounts real
    surface variants not yet in ``phrase_banks.py`` (exactly the gap RFC
    0011 §6.1 says this calibration loop should close over time).
    """
    total = int(table.count().execute())
    if total == 0:
        return {"total_documents": 0, "length": {}, "section_presence_rate": {}}

    lengths = table.texto.length().execute()
    length_stats = {
        "mean": float(lengths.mean()),
        "median": float(lengths.median()),
        "min": int(lengths.min()),
        "max": int(lengths.max()),
    }

    presence: dict[str, float] = {}
    for base_name, phrases in PAIR_PHRASES.items():
        variants = phrases["inicio"]
        present_expr = None
        for variant in variants:
            hit = table.texto.contains(variant)
            present_expr = hit if present_expr is None else (present_expr | hit)
        present_count = int(table.filter(present_expr).count().execute())
        presence[base_name] = present_count / total

    return {
        "total_documents": total,
        "length": length_stats,
        "section_presence_rate": presence,
    }
