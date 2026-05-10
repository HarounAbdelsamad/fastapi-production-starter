"""Tests for the circuit breaker."""

import asyncio

import pytest

from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpen


class TestCircuitBreakerClosed:
    async def test_starts_closed(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        assert cb.state == "closed"

    async def test_successful_call_stays_closed(self):
        cb = CircuitBreaker("test", failure_threshold=3)

        async def ok():
            return "ok"

        result = await cb.call(ok())
        assert result == "ok"
        assert cb.state == "closed"

    async def test_single_failure_does_not_open(self):
        cb = CircuitBreaker("test", failure_threshold=3)

        async def fail():
            raise ValueError("boom")

        with pytest.raises(ValueError):
            await cb.call(fail())
        assert cb.state == "closed"
        assert cb._failure_count == 1

    async def test_threshold_failures_open_circuit(self):
        cb = CircuitBreaker("test", failure_threshold=3)

        async def fail():
            raise ValueError("boom")

        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(fail())

        assert cb.state == "open"

    async def test_success_resets_failure_count(self):
        cb = CircuitBreaker("test", failure_threshold=3)

        async def fail():
            raise ValueError("boom")

        async def ok():
            return "ok"

        with pytest.raises(ValueError):
            await cb.call(fail())
        assert cb._failure_count == 1

        await cb.call(ok())
        assert cb._failure_count == 0


class TestCircuitBreakerOpen:
    async def test_open_circuit_rejects_immediately(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=999)

        async def fail():
            raise ValueError("boom")

        with pytest.raises(ValueError):
            await cb.call(fail())
        assert cb.state == "open"

        async def would_succeed():
            return "ok"

        with pytest.raises(CircuitBreakerOpen) as exc_info:
            await cb.call(would_succeed())
        assert "test" in str(exc_info.value)

    async def test_open_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.01)

        async def fail():
            raise ValueError("boom")

        with pytest.raises(ValueError):
            await cb.call(fail())

        await asyncio.sleep(0.02)

        # Next call should be allowed (half-open probe)
        async def ok():
            return "ok"

        result = await cb.call(ok())
        assert result == "ok"
        assert cb.state == "closed"

    async def test_half_open_failure_reopens_circuit(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.01)

        async def fail():
            raise ValueError("boom")

        with pytest.raises(ValueError):
            await cb.call(fail())

        await asyncio.sleep(0.02)

        with pytest.raises(ValueError):
            await cb.call(fail())

        assert cb.state == "open"


class TestCircuitBreakerContextManager:
    async def test_context_manager_success(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        async with cb:
            pass
        assert cb.state == "closed"

    async def test_context_manager_failure_records_failure(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        with pytest.raises(RuntimeError):
            async with cb:
                raise RuntimeError("fail")
        assert cb._failure_count == 1

    async def test_circuit_breaker_open_not_counted_as_failure(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=999)

        async def fail():
            raise ValueError

        with pytest.raises(ValueError):
            await cb.call(fail())

        count_before = cb._failure_count
        with pytest.raises(CircuitBreakerOpen):
            await cb.call(fail())
        # CircuitBreakerOpen should not increment failure count further
        assert cb.state == "open"
        assert cb._failure_count == count_before
