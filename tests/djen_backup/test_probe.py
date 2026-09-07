"""Tests for djen_backup.probe — the DJEN availability probe worker.

``_probe_one`` calls ``get_caderno_url`` for a single (tribunal, date) pair.
Every other caller of ``get_caderno_url`` in this codebase (``engine.py``'s
checker, ``scripts/drain_unknowns.py``) explicitly catches
``DJENRateLimitedError`` (raised on HTTP 403 — a CloudFront/WAF rate-limit,
never a verdict on absence per CLAUDE.md) and skips the entry for a retry
next run. ``probe.py`` must do the same.
"""

from __future__ import annotations

from datetime import date

import httpx
import pytest
import respx

from djen_backup.probe import _probe_one, _probe_worker
from djen_backup.segments import SegmentWriter


@pytest.mark.asyncio
async def test_probe_one_skips_403_without_raising(tmp_path) -> None:
    delta_writer = SegmentWriter(tmp_path / "probe-delta.csv")
    with respx.mock(assert_all_called=False) as router:
        router.get(url__startswith="https://djen.example/").respond(403)
        async with httpx.AsyncClient() as client:
            await _probe_one("TJSP", date(2024, 1, 2), client, "https://djen.example", delta_writer)

    assert delta_writer.confirmed_count == 0
    assert delta_writer.absent_count == 0


@pytest.mark.asyncio
async def test_probe_worker_keeps_processing_after_a_403(tmp_path) -> None:
    """A 403 on one entry must not silently kill the worker task — the next
    queued entry must still be processed."""
    import asyncio

    delta_writer = SegmentWriter(tmp_path / "probe-delta.csv")
    queue: asyncio.Queue = asyncio.Queue()
    await queue.put(("TJSP", date(2024, 1, 1)))  # will 403
    await queue.put(("TJRO", date(2024, 1, 2)))  # will 404 -> absent
    await queue.put(None)  # sentinel to stop the worker

    with respx.mock(assert_all_called=False) as router:
        router.get(url="https://djen.example/api/v1/caderno/TJSP/2024-01-01/D").respond(403)
        router.get(url__startswith="https://djen.example/").respond(404)
        async with httpx.AsyncClient() as client:
            await _probe_worker(
                queue, client, "https://djen.example", delta_writer, deadline=float("inf")
            )

    assert delta_writer.absent_count == 1
