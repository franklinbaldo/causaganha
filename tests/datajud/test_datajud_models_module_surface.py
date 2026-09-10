"""Module-surface regression guard for datajud/models.py.

data14_bound had zero callers anywhere in the repository outside its own
unit test: src/datajud/client.py never builds a dataAjuizamento range query
with it, and there is no duplicated inline equivalent that could drift.
Removed rather than kept "just in case", per this repository's established
dead-code pattern (PR #1332, PR #1354): unused surface area is a cost even
when the code itself is correct.
"""

from __future__ import annotations

import datajud.models as models_module


def test_dead_data14_bound_helper_was_removed() -> None:
    assert not hasattr(models_module, "data14_bound")
    assert "data14_bound" not in models_module.__all__
