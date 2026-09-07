"""Tests for djen_backup.retry — the shared HTTP retry/backoff policy.

``request_with_retry`` is the single retry primitive used by every DJEN and IA
S3 call in the sync engine (checkers, downloaders, uploaders). These tests
pin down its contract: which conditions actually cause a retry, and what
comes back once retries are exhausted.
"""

from __future__ import annotations

import httpx
import pytest
import tenacity

from djen_backup import retry as retry_module
from djen_backup.retry import request_with_retry


@pytest.fixture
def fast_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retry backoff normally sleeps real seconds (exponential + 15s floor for
    503). The ``request_with_retry`` integration tests only care about call
    counts and the final response, so make every wait instant. The ``_wait``
    unit tests below deliberately don't use this fixture — they assert on
    the real computed durations."""
    monkeypatch.setattr(retry_module, "_wait", lambda retry_state: 0)


def _client(responses: list[httpx.Response]) -> tuple[httpx.AsyncClient, list[int]]:
    """An AsyncClient whose MockTransport returns ``responses`` in order,
    repeating the last one once exhausted, and records how many requests it saw."""
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        idx = min(len(calls), len(responses) - 1)
        calls.append(1)
        return responses[idx]

    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), calls


async def test_retries_on_retriable_status_until_success(fast_wait: None) -> None:
    client, calls = _client([httpx.Response(503), httpx.Response(503), httpx.Response(200)])
    async with client:
        resp = await request_with_retry(client, "GET", "https://example.test/x", max_retries=5)

    assert resp.status_code == 200
    assert len(calls) == 3


async def test_returns_last_response_after_exhausting_retriable_status(fast_wait: None) -> None:
    """A persistent 503 must exhaust retries and hand back that 503 response —
    not raise — so callers can inspect ``resp.status_code`` as documented."""
    client, calls = _client([httpx.Response(503)])
    async with client:
        resp = await request_with_retry(client, "GET", "https://example.test/x", max_retries=2)

    assert resp.status_code == 503
    assert len(calls) == 3  # initial attempt + 2 retries


async def test_does_not_retry_403_by_default(fast_wait: None) -> None:
    """403 (CloudFront/WAF block) is deliberately left to the *next run* —
    see CLAUDE.md: never treat it as absent, but also never burn retry
    budget on it here."""
    client, calls = _client([httpx.Response(403), httpx.Response(200)])
    async with client:
        resp = await request_with_retry(client, "GET", "https://example.test/x", max_retries=5)

    assert resp.status_code == 403
    assert len(calls) == 1


async def test_retries_on_400_only_when_flag_set(fast_wait: None) -> None:
    client, calls = _client([httpx.Response(400), httpx.Response(200)])
    async with client:
        resp = await request_with_retry(
            client, "GET", "https://example.test/x", max_retries=5, retry_djen_400=True
        )

    assert resp.status_code == 200
    assert len(calls) == 2


async def test_does_not_retry_400_without_flag(fast_wait: None) -> None:
    client, calls = _client([httpx.Response(400), httpx.Response(200)])
    async with client:
        resp = await request_with_retry(client, "GET", "https://example.test/x", max_retries=5)

    assert resp.status_code == 400
    assert len(calls) == 1


async def test_retries_on_404_only_when_flag_set(fast_wait: None) -> None:
    client, calls = _client([httpx.Response(404), httpx.Response(200)])
    async with client:
        resp = await request_with_retry(
            client, "GET", "https://example.test/x", max_retries=5, retry_404=True
        )

    assert resp.status_code == 200
    assert len(calls) == 2


async def test_reraises_transport_error_after_exhausting_retries(fast_wait: None) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with client:
        with pytest.raises(httpx.ConnectError):
            await request_with_retry(client, "GET", "https://example.test/x", max_retries=2)


async def test_recovers_from_transport_error(fast_wait: None) -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) < 2:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with client:
        resp = await request_with_retry(client, "GET", "https://example.test/x", max_retries=3)

    assert resp.status_code == 200
    assert len(calls) == 2


def test_wait_enforces_15s_minimum_for_503_without_retry_after() -> None:
    outcome = tenacity.Future(1)
    outcome.set_result(httpx.Response(503))
    retry_state = tenacity.RetryCallState(retry_object=None, fn=None, args=(), kwargs={})
    retry_state.outcome = outcome
    retry_state.attempt_number = 1

    assert retry_module._wait(retry_state) == 15.0


def test_wait_uses_exponential_backoff_for_other_retriable_status() -> None:
    outcome = tenacity.Future(2)
    outcome.set_result(httpx.Response(429))
    retry_state = tenacity.RetryCallState(retry_object=None, fn=None, args=(), kwargs={})
    retry_state.outcome = outcome
    retry_state.attempt_number = 2

    assert retry_module._wait(retry_state) == 4.0
