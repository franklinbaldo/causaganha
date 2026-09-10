from __future__ import annotations

import asyncio
import time
from datetime import date
from pathlib import Path

import httpx
import pytest

from djen_backup import engine as engine_module
from djen_backup.manifest import ManifestEntry, SyncManifest

# Captured at import time, before tests/djen_backup/conftest.py's autouse
# `_fast_sleep` fixture monkeypatches asyncio.sleep to fast-forward any
# delay over 0.05s -- see test_check_only_no_io.py for why this matters.
_REAL_ASYNCIO_SLEEP = asyncio.sleep


def _manifest_with_one_available_entry() -> SyncManifest:
    manifest = SyncManifest()
    key = SyncManifest._key("TJSP", date(2024, 1, 3))
    manifest._entries[key] = ManifestEntry(
        tribunal="TJSP",
        date=date(2024, 1, 3),
        ia_status="",
        djen_status="available",
        djen_raw="200",
    )
    return manifest


def _base_config(*, fail_fast: bool) -> engine_module.SyncConfig:
    return engine_module.SyncConfig(
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
        fail_fast=fail_fast,
    )


@pytest.mark.asyncio
async def test_failed_download_with_fail_fast_sets_abort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``fail_fast`` (default True, documented as 'Stop on first error' in
    __main__.py) is honored by the upload worker (test_upload_worker.py)
    but a download failure -- the far more common failure mode, since it
    covers every DJEN HTTP/network error -- must stop the pipeline too.
    """
    monkeypatch.setattr(asyncio, "sleep", _REAL_ASYNCIO_SLEEP)

    async def _discover_ia_items(manifest: SyncManifest) -> set[tuple[str, int]]:
        return set()

    async def _stage_download(*args: object, **kwargs: object) -> None:
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(engine_module, "_discover_ia_items", _discover_ia_items)
    monkeypatch.setattr(engine_module, "_stage_download", _stage_download)

    manifest = _manifest_with_one_available_entry()
    config = _base_config(fail_fast=True)
    abort_event = asyncio.Event()
    summary = engine_module.SyncSummary()

    await asyncio.wait_for(
        engine_module.run_pipeline(manifest, config, abort_event, summary, time.monotonic() + 5.0),
        timeout=10,
    )

    assert summary.errors == 1
    assert abort_event.is_set()


@pytest.mark.asyncio
async def test_failed_download_without_fail_fast_keeps_abort_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(asyncio, "sleep", _REAL_ASYNCIO_SLEEP)

    async def _discover_ia_items(manifest: SyncManifest) -> set[tuple[str, int]]:
        return set()

    async def _stage_download(*args: object, **kwargs: object) -> None:
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(engine_module, "_discover_ia_items", _discover_ia_items)
    monkeypatch.setattr(engine_module, "_stage_download", _stage_download)

    manifest = _manifest_with_one_available_entry()
    config = _base_config(fail_fast=False)
    abort_event = asyncio.Event()
    summary = engine_module.SyncSummary()

    await asyncio.wait_for(
        engine_module.run_pipeline(manifest, config, abort_event, summary, time.monotonic() + 1.0),
        timeout=10,
    )

    assert summary.errors == 1
    assert not abort_event.is_set()
