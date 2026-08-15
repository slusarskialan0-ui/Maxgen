"""Retry logic with exponential backoff, rate limiting, and timeout handling."""
import time
import logging
import functools
import threading
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)

SOURCE_TIMEOUT = 30  # seconds per source


def retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """Decorator: retry with exponential backoff on exception.

    Args:
        max_attempts: Total number of attempts (including first).
        initial_delay: Seconds to wait before the first retry.
        backoff: Multiplier applied to delay after each retry.
        exceptions: Tuple of exception types that trigger a retry.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exc: Optional[Exception] = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        logger.warning(
                            "Function %s failed after %d attempts: %s",
                            func.__name__,
                            max_attempts,
                            exc,
                        )
                        raise
                    logger.info(
                        "Function %s attempt %d/%d failed (%s). Retrying in %.1fs…",
                        func.__name__,
                        attempt,
                        max_attempts,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                    delay *= backoff
            raise last_exc  # pragma: no cover

        return wrapper
    return decorator


class RateLimiter:
    """Simple in-process token-bucket rate limiter.

    Ensures at most `max_calls` calls per `period` seconds.
    Thread-safe: a lock guards the internal call-timestamp list.
    """

    def __init__(self, max_calls: int = 10, period: float = 1.0):
        self._max_calls = max_calls
        self._period = period
        self._calls: list[float] = []
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            # Drop calls older than one period
            self._calls = [t for t in self._calls if now - t < self._period]
            if len(self._calls) >= self._max_calls:
                sleep_time = self._period - (now - self._calls[0])
            else:
                sleep_time = 0.0
        if sleep_time > 0:
            time.sleep(sleep_time)
        with self._lock:
            self._calls.append(time.monotonic())

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            self.acquire()
            return func(*args, **kwargs)
        return wrapper
