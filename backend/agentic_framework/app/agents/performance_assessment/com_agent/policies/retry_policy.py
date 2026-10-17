"""Exponential backoff retry policy for external tool adapters.

Strictly aligned with:
- PLAN.md Section 12.6 (Factor Tool Error & Retry Policy)
- Catches transient network errors, connection failures, and timeouts.
- Backoff delay formula: base_delay_seconds * 2^(attempt - 1).
"""

import asyncio
import functools
import logging
from typing import Callable, Any, Tuple, Type

logger = logging.getLogger(__name__)


class RetryExhaustedError(Exception):
    """Raised when an external adapter or tool exhausts all retry attempts."""

    def __init__(self, message: str, last_exception: Exception, attempts: int):
        super().__init__(message)
        self.last_exception = last_exception
        self.attempts = attempts


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay_seconds: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        TimeoutError,
        ConnectionError,
        OSError,
    ),
):
    """Decorator applying exponential backoff retry to async functions.

    Formula: delay = base_delay_seconds * (2 ** (attempt - 1))
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception = None  # type: ignore

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as exc:
                    if isinstance(exc, PermissionError):
                        raise exc
                    last_exc = exc
                    logger.warning(
                        f"[{func.__name__}] Attempt {attempt}/{max_attempts} failed with {type(exc).__name__}: {exc}"
                    )
                    if attempt < max_attempts:
                        delay = base_delay_seconds * (2 ** (attempt - 1))
                        if delay > 0:
                            await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"[{func.__name__}] All {max_attempts} attempts exhausted."
                        )
                        raise RetryExhaustedError(
                            f"Function '{func.__name__}' failed after {max_attempts} attempts. Last error: {last_exc}",
                            last_exception=last_exc,
                            attempts=max_attempts,
                        ) from last_exc

        return wrapper

    return decorator
