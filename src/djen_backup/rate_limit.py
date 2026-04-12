"""Async token bucket rate limiter for IA upload throttling."""

from __future__ import annotations

import asyncio
import time


class TokenBucket:
    """Async token bucket rate limiter.

    Allows *burst* uploads immediately, then refills at *rate_per_sec*
    tokens/second. Each call to :meth:`acquire` consumes one token and
    blocks until one is available.

    Example::

        bucket = TokenBucket(rate_per_sec=0.5, burst=4)
        await bucket.acquire()  # blocks if exhausted
    """

    def __init__(self, rate_per_sec: float, burst: int) -> None:
        self._rate = rate_per_sec
        self._capacity = float(burst)
        self._tokens = float(burst)
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Block until a token is available, then consume one."""
        while True:
            async with self._lock:
                now = time.monotonic()
                self._tokens = min(
                    self._capacity,
                    self._tokens + (now - self._updated) * self._rate,
                )
                self._updated = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self._rate
            await asyncio.sleep(wait)
