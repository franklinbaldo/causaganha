"""Circuit breaker's half-open probe must not be wasted by lock contention.

``upload_zip`` orders its guards as (1) circuit breaker ``allow_request()``,
then (2) the per-item ``try_lock`` check. When the breaker is HALF_OPEN,
``allow_request()`` consumes the single probe slot and flips the breaker to
OPEN *before* the lock is checked. If that same call then raises
``ItemBusyError`` (the item is busy, per CLAUDE.md's re-queue contract), the
probe is burned on a call that never touched IA at all — nobody calls
``record_success``/``record_failure`` for it, so the breaker sits OPEN for a
full recovery_timeout with no test performed, even though the outage may
already be over. A concurrent uploader competing for the same item id can
keep re-triggering this every time the breaker reaches half-open.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import httpx
import pytest

from djen_backup.archive import CircuitBreaker, CircuitState, ItemBusyError, _lock_for, upload_zip


if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.asyncio
async def test_item_busy_does_not_consume_half_open_probe(tmp_path: Path) -> None:
    item_id = "djen-tjsp-2099"
    zip_path = tmp_path / "djen-2099-01-02-TJSP.zip"
    zip_path.write_bytes(b"PK\x03\x04")

    breaker = CircuitBreaker(threshold=1, recovery_timeout=60.0)
    breaker.record_failure()  # -> OPEN
    assert breaker.state == CircuitState.OPEN
    breaker._opened_at = time.monotonic() - 61.0  # backdate past recovery_timeout
    assert breaker.state == CircuitState.HALF_OPEN

    # Pre-acquire the per-item lock to simulate a concurrent uploader.
    lock = await _lock_for(item_id)
    await lock.acquire()
    try:
        async with httpx.AsyncClient() as client:
            with pytest.raises(ItemBusyError):
                await upload_zip(client, item_id, zip_path, circuit_breaker=breaker, try_lock=True)
    finally:
        lock.release()

    # The probe must still be available for a genuine (non-busy) attempt --
    # ItemBusyError short-circuited before any IA request was made, so it
    # must not have spent the breaker's one half-open test slot.
    assert breaker.state == CircuitState.HALF_OPEN
