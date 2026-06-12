"""Circuit breaker domain model for provider health management."""

import time
from typing import Any, Dict


class CircuitBreaker:
    """Tracks failure counts and state transitions for a provider endpoint.

    States: CLOSED (normal), OPEN (tripped), HALF_OPEN (probing recovery).
    """

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        if self.state == "HALF_OPEN":
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "time_until_recovery": (
                max(0, self.recovery_timeout - (time.time() - self.last_failure_time))
                if self.state == "OPEN"
                else 0
            ),
        }


def calculate_health_score(
    status: Dict[str, Any], metrics: Dict[str, Any], cb: CircuitBreaker
) -> float:
    """Compute a 0–100 health score from provider status, metrics, and circuit breaker state."""
    score = 100.0

    if status.get("status") != "healthy":
        score -= 30

    if cb.state == "OPEN":
        score -= 40
    elif cb.state == "HALF_OPEN":
        score -= 20

    error_rate = metrics.get("error_rate", 0)
    if error_rate > 10:
        score -= 20
    elif error_rate > 5:
        score -= 10
    elif error_rate > 1:
        score -= 5

    avg_time = metrics.get("avg_response_time", 0)
    if avg_time > 5000:
        score -= 10
    elif avg_time > 2000:
        score -= 5

    return max(0, round(score, 1))
