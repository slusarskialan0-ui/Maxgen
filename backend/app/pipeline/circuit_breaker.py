"""Simple in-memory circuit breaker for unstable lead sources."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from config import CIRCUIT_BREAKER_FAILURE_THRESHOLD, CIRCUIT_BREAKER_RECOVERY_SECONDS


@dataclass
class CircuitState:
    failures: int = 0
    open_until: float = 0.0


class SourceCircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        recovery_seconds: int = CIRCUIT_BREAKER_RECOVERY_SECONDS,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._states: dict[str, CircuitState] = {}
        self._lock = threading.Lock()

    def is_open(self, key: str) -> bool:
        with self._lock:
            state = self._states.get(key)
            return bool(state and state.open_until > time.time())

    def remaining_open_seconds(self, key: str) -> int:
        with self._lock:
            state = self._states.get(key)
            if not state:
                return 0
            return max(0, int(state.open_until - time.time()))

    def record_success(self, key: str) -> None:
        with self._lock:
            self._states[key] = CircuitState(failures=0, open_until=0.0)

    def record_failure(self, key: str) -> bool:
        with self._lock:
            state = self._states.get(key, CircuitState())
            state.failures += 1
            if state.failures >= self.failure_threshold:
                state.open_until = time.time() + self.recovery_seconds
                state.failures = 0
                self._states[key] = state
                return True
            self._states[key] = state
            return False


source_circuit_breaker = SourceCircuitBreaker()
