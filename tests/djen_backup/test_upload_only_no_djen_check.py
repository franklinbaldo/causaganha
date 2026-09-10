from __future__ import annotations

import asyncio
import time
from datetime import date
from pathlib import Path

import pytest

from djen_backup import engine as engine_module
from djen_backup.manifest import ManifestEntry, SyncManifest

# Captured at import time, before tests/djen_backup/conftest.py's autouse
# `_fast_sleep` fixture monkeypatches asyncio.sleep to fast-forward any
# delay over 0.05s -- see test_check_only_no_io.py for why this matters.
_REAL_ASYNCIO_SLEEP = asyncio.sleep


@pytest.mark.asyncio
async def test_upload_only_never_checks_djen_for_unknown_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """djen-backup upload is documented as draining already-discovered
    available entries ('Upload already-discovered available entries
    (backlog drain)' -- __main__.py's upload() docstring; CLAUDE.md's
    '# Only upload already-available entries'). It must never probe DJEN
    for an entry whose availability isn't already known, even when one is
    on the manifest.
    """
    monkeypatch.setattr(asyncio, "sleep", _REAL_ASYNCIO_SLEEP)

    manifest = SyncManifest()
    key = SyncManifest._key("TJSP", date(2024, 1, 3))
    manifest._entries[key] = ManifestEntry(
        tribunal="TJSP",
        date=date(2024, 1, 3),
        ia_status="",
        djen_status="",
        djen_raw="",
    )

    called = {"checked": False}

    async def _get_caderno_url(*args: object, **kwargs: object) -> str:
        called["checked"] = True
        msg = "DJEN must not be probed in upload-only mode"
        raise AssertionError(msg)

    async def _discover_ia_items(manifest: SyncManifest) -> set[tuple[str, int]]:
        return set()

    monkeypatch.setattr(engine_module, "get_caderno_url", _get_caderno_url)
    monkeypatch.setattr(engine_module, "_discover_ia_items", _discover_ia_items)

    config = engine_module.SyncConfig(
        start_date=date(2024, 1, 3),
        lower_bound=date(2024, 1, 1),
        tribunal="TJSP",
        deadline_minutes=1,
        max_items=0,
        workers=1,
        manifest_file=Path("unused-manifest.csv"),
        djen_proxy_url="https://example.invalid",
        ia_auth="LOW dry-run:dry-run",
        dry_run=True,
        upload_only=True,
    )

    abort_event = asyncio.Event()
    summary = engine_module.SyncSummary()

    await asyncio.wait_for(
        engine_module.run_pipeline(manifest, config, abort_event, summary, time.monotonic() + 1.0),
        timeout=10,
    )

    assert called == {"checked": False}
    assert manifest._entries[key].djen_raw == ""
