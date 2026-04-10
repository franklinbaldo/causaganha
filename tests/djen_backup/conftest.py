"""Shared fixtures for djen_backup BDD tests."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
import respx


# ── Fixtures ────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _fast_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace asyncio.sleep with a near-instant version.

    Preserves tiny sleeps (<=0.05s) used for concurrency simulation,
    but eliminates upload cooldowns and retry backoffs.
    """
    _real_sleep = asyncio.sleep

    async def _instant_sleep(delay: float, *args: object, **kwargs: object) -> None:
        if delay <= 0.05:
            await _real_sleep(delay)
        else:
            await _real_sleep(0)

    monkeypatch.setattr(asyncio, "sleep", _instant_sleep)


@pytest.fixture
def mock_api() -> respx.MockRouter:
    """A ``respx`` mock router activated for the test."""
    with respx.mock(assert_all_called=False) as router:
        router.head(url__startswith="https://archive.org/download/").respond(404)
        yield router


@pytest.fixture
def context() -> dict[str, Any]:
    """A mutable bag for sharing data across Given/When/Then steps."""
    return {}
