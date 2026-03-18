"""BDD steps for the circuit breaker feature."""

from __future__ import annotations

import asyncio
import time

from pytest_bdd import given, parsers, scenario, then, when

from djen_backup.archive import CircuitBreaker, CircuitState

# ── Scenarios ────────────────────────────────────────────────────────


@scenario("../circuit_breaker.feature", "Circuit opens after 5 consecutive failures")
def test_circuit_opens() -> None:
    pass


@scenario("../circuit_breaker.feature", "Circuit enters half-open after recovery timeout")
def test_half_open() -> None:
    pass


@scenario("../circuit_breaker.feature", "Successful test request closes the circuit")
def test_circuit_closes() -> None:
    pass


# ── Given ────────────────────────────────────────────────────────────


@given(
    parsers.parse("the circuit breaker threshold is {n:d}"),
    target_fixture="circuit_breaker",
)
def given_breaker_threshold(n: int) -> CircuitBreaker:
    return CircuitBreaker(threshold=n, recovery_timeout=60.0)


@given(parsers.parse("the recovery timeout is {n:d} second"))
def given_recovery_timeout(circuit_breaker: CircuitBreaker, n: int) -> None:
    circuit_breaker._recovery_timeout = float(n)
    circuit_breaker._base_recovery = float(n)


# ── When ─────────────────────────────────────────────────────────────


@when(parsers.parse("{n:d} consecutive IA uploads fail"))
def when_n_failures(circuit_breaker: CircuitBreaker, n: int) -> None:
    async def _run() -> None:
        for _ in range(n):
            await circuit_breaker.record_failure()

    asyncio.run(_run())


@when("I wait for the recovery timeout")
def when_wait_recovery(circuit_breaker: CircuitBreaker) -> None:
    # Simulate passage of time by back-dating _opened_at
    circuit_breaker._opened_at = time.monotonic() - circuit_breaker._recovery_timeout - 1


@when("the test request succeeds")
def when_test_succeeds(circuit_breaker: CircuitBreaker) -> None:
    async def _run() -> None:
        allowed = await circuit_breaker.allow_request()
        assert allowed, "Expected half-open circuit to allow a test request"
        await circuit_breaker.record_success()

    asyncio.run(_run())


# ── Then ─────────────────────────────────────────────────────────────


@then("the circuit breaker should be open")
def then_open(circuit_breaker: CircuitBreaker) -> None:
    assert circuit_breaker.state == CircuitState.OPEN


@then("the next upload request should be skipped")
def then_request_skipped(circuit_breaker: CircuitBreaker) -> None:
    allowed = asyncio.run(circuit_breaker.allow_request())
    assert not allowed


@then("the circuit breaker should be half-open")
def then_half_open(circuit_breaker: CircuitBreaker) -> None:
    assert circuit_breaker.state == CircuitState.HALF_OPEN


@then("one test request should be allowed")
def then_one_allowed(circuit_breaker: CircuitBreaker) -> None:
    allowed = asyncio.run(circuit_breaker.allow_request())
    assert allowed


@then("the circuit breaker should be closed")
def then_closed(circuit_breaker: CircuitBreaker) -> None:
    assert circuit_breaker.state == CircuitState.CLOSED
