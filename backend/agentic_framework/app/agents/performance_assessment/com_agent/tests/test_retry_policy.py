"""Unit tests for exponential backoff retry policy (T2.1)."""

import pytest
import time
from app.agents.performance_assessment.com_agent.policies.retry_policy import (
    retry_with_backoff,
    RetryExhaustedError,
)

@pytest.mark.asyncio
async def test_retry_success_on_first_try():
    calls = 0

    @retry_with_backoff(max_attempts=3, base_delay_seconds=0.001)
    async def sample_func():
        nonlocal calls
        calls += 1
        return "success"

    result = await sample_func()
    assert result == "success"
    assert calls == 1

@pytest.mark.asyncio
async def test_retry_success_after_transient_failures():
    calls = 0

    @retry_with_backoff(max_attempts=3, base_delay_seconds=0.001)
    async def flakey_func():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ConnectionError(f"Temporary network blip #{calls}")
        return "recovered"

    result = await flakey_func()
    assert result == "recovered"
    assert calls == 3

@pytest.mark.asyncio
async def test_retry_exhausted_raises_exception():
    calls = 0

    @retry_with_backoff(max_attempts=3, base_delay_seconds=0.001)
    async def always_failing():
        nonlocal calls
        calls += 1
        raise TimeoutError("GitHub connection timed out")

    with pytest.raises(RetryExhaustedError) as exc_info:
        await always_failing()

    assert calls == 3
    assert exc_info.value.attempts == 3
    assert isinstance(exc_info.value.last_exception, TimeoutError)

@pytest.mark.asyncio
async def test_non_retryable_exception_fails_immediately():
    calls = 0

    @retry_with_backoff(max_attempts=3, base_delay_seconds=0.001)
    async def logic_error_func():
        nonlocal calls
        calls += 1
        raise ValueError("Invalid student ID format")

    with pytest.raises(ValueError):
        await logic_error_func()

    assert calls == 1

@pytest.mark.asyncio
async def test_backoff_timing_progression():
    delays = []

    @retry_with_backoff(max_attempts=3, base_delay_seconds=0.02)
    async def timed_func():
        nonlocal delays
        delays.append(time.perf_counter())
        raise OSError("Socket unavailable")

    with pytest.raises(RetryExhaustedError):
        await timed_func()

    assert len(delays) == 3
    # Interval between 1st and 2nd should be >= 0.015s (nominal 0.02s)
    # Interval between 2nd and 3rd should be >= 0.030s (nominal 0.04s)
    interval_1 = delays[1] - delays[0]
    interval_2 = delays[2] - delays[1]
    assert interval_1 >= 0.015
    assert interval_2 >= 0.030
    assert interval_2 > interval_1
