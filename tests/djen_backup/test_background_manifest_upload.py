"""Regression test for the periodic background manifest-segment upload.

``run_pipeline``'s periodic IA upload ("every 10 min protects against
crashes", per CLAUDE.md) is fired via a bare ``asyncio.create_task(...)``
with no reference kept anywhere. Per the asyncio docs, a task with no
strong reference elsewhere may be garbage-collected before it completes,
and nothing in ``run_pipeline``'s shutdown sequence joins it either -- so
the safety-net upload can be silently abandoned instead of completing.
``run_pipeline`` must hold a reference to every background upload task and
wait for any still-pending ones before returning.
"""

from __future__ import annotations

import asyncio
import time
from datetime import date
from pathlib import Path

import pytest

from djen_backup import engine as engine_module
from djen_backup.djen import DJENNotFoundError
from djen_backup.manifest import ManifestEntry, SyncManifest

# Captured at import time, before conftest.py's autouse `_fast_sleep`
# fixture monkeypatches asyncio.sleep to fast-forward any delay over
# 0.05s. This test needs the deadline_monitor's real sleep so its 5s
# deadline doesn't collapse to instant and abort the checker phase before
# it ever triggers the background upload.
_REAL_ASYNCIO_SLEEP = asyncio.sleep


@pytest.mark.asyncio
async def test_run_pipeline_waits_for_background_manifest_upload_before_returning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(asyncio, "sleep", _REAL_ASYNCIO_SLEEP)
    monkeypatch.setattr(engine_module, "IA_UPLOAD_INTERVAL_SECONDS", 0.0)

    manifest = SyncManifest()
    key = SyncManifest._key("TJSP", date(2024, 1, 3))
    manifest._entries[key] = ManifestEntry(
        tribunal="TJSP",
        date=date(2024, 1, 3),
        ia_status="",
        djen_status="",
        djen_raw="",
    )

    async def _discover_ia_items(manifest: SyncManifest) -> set[tuple[str, int]]:
        return set()

    async def _get_caderno_url(client, base_url, tribunal, d):
        raise DJENNotFoundError(status_code=404, reason="Not Found")

    upload_started = asyncio.Event()
    release_upload = asyncio.Event()
    completed = {"segment": False}

    async def _upload_segment_to_ia(self: SyncManifest, ia_auth: str) -> bool:
        upload_started.set()
        await release_upload.wait()
        completed["segment"] = True
        return True

    async def _upload_summary_to_ia(self: SyncManifest, ia_auth: str) -> bool:
        return True

    monkeypatch.setattr(engine_module, "_discover_ia_items", _discover_ia_items)
    monkeypatch.setattr(engine_module, "get_caderno_url", _get_caderno_url)
    monkeypatch.setattr(SyncManifest, "upload_segment_to_ia", _upload_segment_to_ia)
    monkeypatch.setattr(SyncManifest, "upload_summary_to_ia", _upload_summary_to_ia)

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
        dry_run=False,
        check_only=True,
    )

    abort_event = asyncio.Event()
    summary = engine_module.SyncSummary()

    pipeline_task = asyncio.create_task(
        engine_module.run_pipeline(manifest, config, abort_event, summary, time.monotonic() + 5.0)
    )

    await asyncio.wait_for(upload_started.wait(), timeout=5)

    # Give the buggy (unfixed) code ample real wall-clock time to finish
    # and return -- it has nothing left to do once the checker phase is
    # done, so 0.5s is generous. The fixed code must still be genuinely
    # blocked here: nothing but setting release_upload can unblock it.
    done, pending = await asyncio.wait({pipeline_task}, timeout=0.5)
    assert pipeline_task in pending, (
        "run_pipeline returned while its own background manifest-segment "
        "upload was still in flight -- the periodic-upload safety net "
        "(CLAUDE.md: 'protects against crashes') can be silently "
        "abandoned instead of completing before shutdown"
    )

    release_upload.set()
    await asyncio.wait_for(pipeline_task, timeout=5)

    assert completed["segment"] is True
