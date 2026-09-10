"""download_zip's segmented path must not orphan sibling segment downloads.

Before this fix, download_zip appended bare coroutines to ``tasks`` and
awaited ``asyncio.gather(*tasks)`` directly. ``asyncio.gather`` wraps each
awaitable into a ``Task`` and schedules all of them immediately, but when one
segment raises, it does *not* cancel the still-pending sibling tasks -- they
keep running in the background, orphaned from the caller, after
``download_zip`` has already propagated the failure. That wastes DJEN
rate-limit budget and open connections on a download that already failed,
with the sibling segments' results silently discarded.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from djen_backup import djen as djen_module


@pytest.mark.asyncio
async def test_download_zip_cancels_sibling_segments_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cancelled_starts: set[int] = set()
    completed_starts: set[int] = set()

    async def fake_segment(_client: httpx.AsyncClient, _url: str, start: int, end: int) -> bytes:
        if start == 0:
            msg = "segment 0 failed"
            raise ValueError(msg)
        # An Event that is never set never resolves on its own -- unlike a
        # timed sleep, there is no wall-clock race to get wrong (and this
        # package's own conftest.py autouse fixture fast-forwards any
        # asyncio.sleep() longer than 0.05s, which would otherwise mask the
        # very bug this test exists to catch). The only way this coroutine
        # ever finishes is via cancellation.
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled_starts.add(start)
            raise
        completed_starts.add(start)  # pragma: no cover - unreachable if fixed
        return b"x" * (end - start + 1)

    monkeypatch.setattr(djen_module, "_download_segment", fake_segment)

    with respx.mock(assert_all_called=False) as router:
        router.get("https://djen.example/djen.zip").respond(
            206,
            content=b"",
            headers={"Content-Range": "bytes 0-0/20000000"},
        )
        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match="segment 0 failed"):
                await djen_module.download_zip(client, "https://djen.example/djen.zip")

    # Let the cancellation callbacks scheduled by download_zip's own cleanup
    # run; this is far shorter than the siblings' 3600s sleep, so anything
    # observed here can only be the result of an actual cancel(), not a race.
    await asyncio.sleep(0.1)

    assert cancelled_starts == {5000000, 10000000, 15000000}, (
        "sibling segment downloads were not cancelled after download_zip "
        f"raised -- cancelled={cancelled_starts} completed={completed_starts}"
    )
    assert completed_starts == set()
