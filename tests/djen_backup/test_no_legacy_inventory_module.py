"""djen_backup.manifest.SyncManifest is the single source of truth (see CLAUDE.md).

manifest.py's own docstring says SyncManifest "Replaces both ZipInventory and
SyncState." The old ZipInventory implementation in djen_backup/inventory.py
was left behind after that migration: nothing in src/, scripts/, or the
workflows imports it, and it carried zero test coverage. Keeping a second,
unused (tribunal, date) -> status mechanism around invites exactly the kind
of "which source is canonical" confusion CLAUDE.md warns about for the CSV
manifest. This test locks in that the legacy module stays deleted.
"""

from __future__ import annotations

import importlib

import pytest


def test_legacy_zip_inventory_module_is_gone() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("djen_backup.inventory")
