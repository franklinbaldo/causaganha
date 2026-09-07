"""Circuit breaker for IA uploads — single source of truth.

Lives in its own module so both ``djen_backup.archive`` (async upload
pipeline) and ``causaganha.pipeline.ia_s3`` (sync legacy callers) can
import it without creating a cycle.

``record_success`` / ``record_failure`` / ``is_open`` are sync so the
same instance can be shared by sync and async callers. ``allow_request``
stays async because async callers expect to ``await`` it; internally it
uses the same threading lock as the sync methods.
"""

from __future__ import annotations

import threading
import time
from enum import StrEnum

import structlog


log = structlog.get_logger()


class CircuitState(StrEnum):
    """States for the circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker with half-open recovery.

    - CLOSED: normal operation, count consecutive failures.
    - OPEN: after *threshold* failures, refuse requests for *recovery_timeout* seconds.
    - HALF_OPEN: after timeout elapses, allow **one** test request.
      Success → CLOSED.  Failure → OPEN with doubled timeout (capped at 5 min).
    """

    def __init__(
        self,
        threshold: int = 5,
        recovery_timeout: float = 60.0,
    ) -> None:
        """Initialize the circuit breaker with failure threshold and recovery timeout."""
        self._threshold = threshold
        self._base_recovery = recovery_timeout
        self._recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._opened_at = 0.0
        self._probing = False
        self.was_opened = False
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        """Return the current state (for external inspection / tests)."""
        if (
            self._state == CircuitState.OPEN
            and time.monotonic() - self._opened_at >= self._recovery_timeout
        ):
            return CircuitState.HALF_OPEN
        return self._state

    @property
    def is_open(self) -> bool:
        """Sync open-check for callers that don't drive the async probe slot.

        Returns True only for OPEN — HALF_OPEN is "ready to probe" so callers
        that drive the state machine via ``allow_request`` see a chance to
        recover. Reads the dynamic ``state`` (not raw ``_state``): once
        ``recovery_timeout`` elapses, a sync caller that never calls
        ``allow_request``/``record_success`` still sees the circuit become
        probeable instead of staying open forever.
        """
        return self.state == CircuitState.OPEN

    def _state_locked(self) -> CircuitState:
        """Compute state while the lock is held (avoids TOCTOU)."""
        if (
            self._state == CircuitState.OPEN
            and time.monotonic() - self._opened_at >= self._recovery_timeout
        ):
            return CircuitState.HALF_OPEN
        return self._state

    async def allow_request(self) -> bool:
        """Check if a request is allowed by the circuit breaker."""
        # threading.Lock is held briefly for state mutation; safe in async.
        with self._lock:
            s = self._state_locked()
            if s == CircuitState.CLOSED:
                return True
            if s == CircuitState.HALF_OPEN:
                # Consume the probe slot — transition to OPEN so only one
                # worker gets through while the test request is in-flight.
                # Track it explicitly: by the time record_failure() runs,
                # _state/_opened_at already reflect this OPEN transition, so
                # re-deriving "was this the half-open probe?" from state
                # would always see a freshly-opened circuit, never HALF_OPEN.
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                self._probing = True
                return True
            return False

    def record_success(self) -> None:
        """Record a successful request and reset the circuit."""
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED
            self._recovery_timeout = self._base_recovery
            self._probing = False

    def record_failure(self) -> None:
        """Record a failed request and update circuit state accordingly."""
        with self._lock:
            self._failure_count += 1
            was_open = self._state == CircuitState.OPEN
            was_half_open_probe = self._probing or self._state_locked() == CircuitState.HALF_OPEN
            if was_half_open_probe:
                # Test request failed — reopen with increased timeout. This
                # also covers a sync caller (ia_s3.py) that only checks
                # ``is_open``/``state`` and never calls ``allow_request``, so
                # ``_probing`` is never set: without also checking the
                # dynamic half-open state here, ``_opened_at`` would never
                # advance and the next call would immediately see the same
                # elapsed recovery_timeout and allow another unthrottled retry.
                self._probing = False
                self._recovery_timeout = min(self._recovery_timeout * 2, 300.0)
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                self.was_opened = True
                log.warning(
                    "circuit_breaker_reopen",
                    next_retry_s=self._recovery_timeout,
                )
            elif self._failure_count >= self._threshold and not was_open:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                self.was_opened = True
                log.error(
                    "circuit_breaker_open",
                    failures=self._failure_count,
                    recovery_s=self._recovery_timeout,
                )
