"""reset_manifest must actually force a DJEN recheck, not silently no-op.

engine.py's check-priority builder treats djen_raw (not djen_status) as the
canonical terminal signal (engine.py:417-422, deliberately, so a stale
djen_status can't hide a re-checkable row). reset_manifest must clear
djen_raw too, or the entries it "resets" stay terminal from the checker's
point of view.
"""

from __future__ import annotations

from datetime import date

from djen_backup.manifest import ManifestEntry, SyncManifest, interpret_djen_raw
from djen_backup.service import reset_manifest


def _write_manifest(path, entry: ManifestEntry) -> None:
    manifest = SyncManifest()
    manifest._entries[(entry.tribunal, entry.date)] = entry  # noqa: SLF001
    manifest.save_to_disk(path)


def test_reset_clears_djen_raw_so_entry_is_no_longer_terminal(tmp_path) -> None:
    manifest_file = tmp_path / "sync-manifest.csv"
    _write_manifest(
        manifest_file,
        ManifestEntry(
            tribunal="TJRO",
            date=date(2024, 1, 1),
            ia_status="",
            djen_status="absent",
            djen_raw="404",
            updated_at="2024-01-01T00:00:00Z",
        ),
    )

    result = reset_manifest(manifest_file, tribunal="TJRO", reset_all=False)
    assert result.count == 1

    reloaded = SyncManifest()
    reloaded.load_from_disk(manifest_file)
    entry = next(iter(reloaded._entries.values()))  # noqa: SLF001

    assert entry.djen_status == ""
    assert entry.ia_status == ""
    assert entry.djen_raw == ""
    assert interpret_djen_raw(entry.djen_raw) == ""


def test_reset_all_clears_djen_raw_across_tribunals(tmp_path) -> None:
    manifest_file = tmp_path / "sync-manifest.csv"
    manifest = SyncManifest()
    manifest._entries[("TJRO", date(2024, 1, 1))] = ManifestEntry(  # noqa: SLF001
        tribunal="TJRO", date=date(2024, 1, 1), djen_status="available", djen_raw="200"
    )
    manifest._entries[("TJSP", date(2024, 1, 1))] = ManifestEntry(  # noqa: SLF001
        tribunal="TJSP", date=date(2024, 1, 1), djen_status="absent", djen_raw="400"
    )
    manifest.save_to_disk(manifest_file)

    result = reset_manifest(manifest_file, tribunal=None, reset_all=True)
    assert result.count == 2

    reloaded = SyncManifest()
    reloaded.load_from_disk(manifest_file)
    for entry in reloaded._entries.values():  # noqa: SLF001
        assert entry.djen_raw == ""
        assert interpret_djen_raw(entry.djen_raw) == ""
