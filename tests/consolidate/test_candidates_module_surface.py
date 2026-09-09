"""Module-surface regression guard for candidates.py.

tribunal_years_needing_consolidation_from_ia had zero callers and zero
tests anywhere in the repository, and its item_id parsing
(``split_part(item_id, '-', -2)`` for the tribunal segment) mis-parses
hyphenated tribunal codes such as TRE-* (e.g. ``djen-tre-ro-2025`` would
yield tribunal ``"ro"`` instead of ``"tre-ro"``). Removed rather than
fixed, per this repository's established dead-code pattern: a bug in code
nothing calls delivers no product value to repair.
"""

from __future__ import annotations

import causaganha.consolidate.candidates as candidates_module


def test_dead_tribunal_year_helper_was_removed() -> None:
    assert not hasattr(candidates_module, "tribunal_years_needing_consolidation_from_ia")
