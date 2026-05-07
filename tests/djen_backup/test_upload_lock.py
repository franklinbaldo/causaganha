"""Per-item upload lock behavior — try_lock must raise ItemBusyError.

CLAUDE.md mandates re-queueing on ItemBusyError; the engine's upload_worker
implements that re-queue, but the contract upload_zip relies on is that the
exception fires when the lock is held.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import httpx
import pytest

from djen_backup.archive import ItemBusyError, _lock_for, upload_zip


if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.asyncio
async def test_upload_zip_try_lock_raises_when_item_busy(tmp_path: Path) -> None:
    item_id = "djen-tjsp-2024"
    zip_path = tmp_path / "djen-2024-01-02-TJSP.zip"
    zip_path.write_bytes(b"PK\x03\x04")

    # Pre-acquire the per-item lock to simulate a concurrent uploader.
    lock = await _lock_for(item_id)
    await lock.acquire()
    try:
        async with httpx.AsyncClient() as client:
            with pytest.raises(ItemBusyError):
                await upload_zip(client, item_id, zip_path, try_lock=True)
    finally:
        lock.release()


@pytest.mark.asyncio
async def test_lock_for_returns_same_instance_for_same_item() -> None:
    a = await _lock_for("djen-test-2024")
    b = await _lock_for("djen-test-2024")
    assert a is b
    c = await _lock_for("djen-test-2025")
    assert c is not a


@pytest.mark.asyncio
async def test_distinct_items_can_upload_concurrently() -> None:
    # Two distinct item_ids should have independent locks — both can be held.
    lock_a = await _lock_for("djen-tjsp-2024")
    lock_b = await _lock_for("djen-tjba-2024")
    await asyncio.wait_for(lock_a.acquire(), timeout=1)
    try:
        await asyncio.wait_for(lock_b.acquire(), timeout=1)
        lock_b.release()
    finally:
        lock_a.release()
