"""Circuit breaker reference implementation.

Three-state Fowler pattern (CLOSED → OPEN → HALF-OPEN → CLOSED).

Usage::

    breaker = CircuitBreaker("payments-api", failure_threshold=5, recovery_timeout=60)

    # Context-manager style:
    async def call_payments():
        async with breaker:
            return await client.get("https://payments.example.com/status")

    # Explicit call style:
    result = await breaker.call(client.get("https://payments.example.com/status"))

See ``docs/operations/circuit-breakers.md`` for state-transition details.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable
from typing import Any


class CircuitBreakerOpen(Exception):  # noqa: N818
    """Raised when a call is rejected because the circuit is open."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Circuit '{name}' is open — call rejected")
        self.name = name


class CircuitBreaker:
    """Async-safe circuit breaker.

    Parameters
    ----------
    name:
        Human-readable identifier (appears in exceptions and logs).
    failure_threshold:
        Consecutive failures needed to open the circuit.
    recovery_timeout:
        Seconds in OPEN state before moving to HALF-OPEN.
    half_open_max_calls:
        Max concurrent probe calls in HALF-OPEN state (default 1).
    """

    def __init__(
        self,
        name: str,
        *,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = "closed"
        self._failure_count = 0
        self._opened_at: float | None = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        return self._state

    async def _check_and_maybe_transition(self) -> None:
        """Raise if the call should be rejected; transition OPEN→HALF-OPEN if ready."""
        async with self._lock:
            if self._state == "open":
                elapsed = time.monotonic() - (self._opened_at or 0)
                if elapsed >= self.recovery_timeout:
                    self._state = "half-open"
                    self._half_open_calls = 0
                else:
                    raise CircuitBreakerOpen(self.name)
            if self._state == "half-open":
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerOpen(self.name)
                self._half_open_calls += 1

    async def record_success(self) -> None:
        """Call after a successful downstream call; resets to CLOSED."""
        async with self._lock:
            self._state = "closed"
            self._failure_count = 0
            self._opened_at = None
            self._half_open_calls = 0

    async def record_failure(self) -> None:
        """Call after a failed downstream call; may open the circuit."""
        async with self._lock:
            if self._state == "half-open":
                self._state = "open"
                self._opened_at = time.monotonic()
                return
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._state = "open"
                self._opened_at = time.monotonic()

    async def call(self, coro: Awaitable[Any]) -> Any:
        """Execute *coro* with circuit-breaker protection.

        Raises :class:`CircuitBreakerOpen` without awaiting *coro* when the
        circuit is open.  Re-raises the original exception on downstream failure
        (after incrementing the failure counter).
        """
        await self._check_and_maybe_transition()
        try:
            result = await coro
            await self.record_success()
            return result
        except CircuitBreakerOpen:
            raise
        except Exception:
            await self.record_failure()
            raise

    async def __aenter__(self) -> CircuitBreaker:
        await self._check_and_maybe_transition()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is None:
            await self.record_success()
        elif exc_type is not CircuitBreakerOpen:
            await self.record_failure()
