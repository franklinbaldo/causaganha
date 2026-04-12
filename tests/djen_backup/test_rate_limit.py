"""Unit tests for the async TokenBucket rate limiter."""

from __future__ import annotations

import asyncio
import time

import pytest

from djen_backup.rate_limit import TokenBucket


@pytest.mark.asyncio
async def test_burst_drains_without_waiting() -> None:
    """Burst capacity should be immediately available without any sleep."""
    bucket = TokenBucket(rate_per_sec=0.1, burst=4)
    start = time.monotonic()
    for _ in range(4):
        await bucket.acquire()
    elapsed = time.monotonic() - start
    # All 4 burst tokens should be consumed near-instantly
    assert elapsed < 0.1


@pytest.mark.asyncio
async def test_acquire_blocks_when_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 5th acquire on a burst=4 bucket should call asyncio.sleep."""
    sleep_calls: list[float] = []
    real_sleep = asyncio.sleep

    async def capture_sleep(delay: float, *args: object, **kwargs: object) -> None:
        sleep_calls.append(delay)
        await real_sleep(0)

    monkeypatch.setattr(asyncio, "sleep", capture_sleep)

    bucket = TokenBucket(rate_per_sec=0.5, burst=4)
    for _ in range(4):
        await bucket.acquire()
    await bucket.acquire()  # 5th — bucket exhausted, must sleep

    assert len(sleep_calls) >= 1
    assert sleep_calls[0] > 0


@pytest.mark.asyncio
async def test_tokens_replenish_over_time() -> None:
    """Tokens refill at the configured rate after the burst is consumed."""
    bucket = TokenBucket(rate_per_sec=10.0, burst=1)
    await bucket.acquire()  # drain

    # Simulate 0.2 s of elapsed time by manipulating _updated
    bucket._updated -= 0.2

    # At 10 tokens/s, 0.2 s → 2 tokens refilled; should not need to sleep
    start = time.monotonic()
    await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.05


@pytest.mark.asyncio
async def test_capacity_cap() -> None:
    """Tokens must not exceed capacity even after a long idle period."""
    bucket = TokenBucket(rate_per_sec=100.0, burst=3)
    # Simulate a long idle period
    bucket._updated -= 1000.0

    # Should still only have 3 tokens (capacity=3)
    for _ in range(3):
        await bucket.acquire()

    # 4th should require waiting (all burst consumed)
    sleep_calls: list[float] = []
    real_sleep = asyncio.sleep

    async def capture_sleep(delay: float, *args: object, **kwargs: object) -> None:
        sleep_calls.append(delay)
        await real_sleep(0)

    import asyncio as _asyncio

    _asyncio.sleep = capture_sleep  # type: ignore[method-assign]
    try:
        await bucket.acquire()
    finally:
        _asyncio.sleep = real_sleep  # type: ignore[method-assign]

    assert len(sleep_calls) >= 1


@pytest.mark.asyncio
async def test_concurrent_acquires_are_serialized() -> None:
    """Concurrent acquires should each get exactly one token."""
    bucket = TokenBucket(rate_per_sec=1000.0, burst=10)
    results: list[int] = []

    async def worker(n: int) -> None:
        await bucket.acquire()
        results.append(n)

    await asyncio.gather(*[worker(i) for i in range(10)])
    assert sorted(results) == list(range(10))
