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
# delay over 0.05s. This test needs the deadline_monitor's real sleep so
# the other pipeline tasks get genuine wall-clock room to run before the
# deadline cuts them off -- fast-forwarding it would race the deadline
# against task startup and pass/fail based on scheduling luck rather than
# on whether check_only actually gates the download/upload workers.
_REAL_ASYNCIO_SLEEP = asyncio.sleep


@pytest.mark.asyncio
async def test_check_only_never_downloads_or_uploads_backlog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """djen-backup check is documented as 'no I/O' (CLAUDE.md) -- it must
    never drain an existing available/not-yet-uploaded backlog entry into
    the download/upload workers, even when one is already on the manifest.
    """
    monkeypatch.setattr(asyncio, "sleep", _REAL_ASYNCIO_SLEEP)

    manifest = SyncManifest()
    key = SyncManifest._key("TJSP", date(2024, 1, 3))
    manifest._entries[key] = ManifestEntry(
        tribunal="TJSP",
        date=date(2024, 1, 3),
        ia_status="",
        djen_status="available",
        djen_raw="200",
    )

    called: dict[str, bool] = {"download": False, "upload": False}

    async def _stage_download(*args: object, **kwargs: object) -> None:
        called["download"] = True
        msg = "download must not run in check-only mode"
        raise AssertionError(msg)

    async def _upload_zip(*args: object, **kwargs: object) -> bool:
        called["upload"] = True
        msg = "upload must not run in check-only mode"
        raise AssertionError(msg)

    async def _discover_ia_items(manifest: SyncManifest) -> set[tuple[str, int]]:
        return set()

    monkeypatch.setattr(engine_module, "_stage_download", _stage_download)
    monkeypatch.setattr(engine_module, "upload_zip", _upload_zip)
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
        check_only=True,
    )

    abort_event = asyncio.Event()
    summary = engine_module.SyncSummary()

    await asyncio.wait_for(
        engine_module.run_pipeline(manifest, config, abort_event, summary, time.monotonic() + 1.0),
        timeout=10,
    )

    assert called == {"download": False, "upload": False}
    assert manifest._entries[key].ia_status == ""
