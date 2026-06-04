import statistics
import time
from collections import defaultdict
from typing import Any, Dict, List


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
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


class PerformanceMetrics:
    def __init__(self):
        self.response_times: Dict[str, List[float]] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.total_requests: Dict[str, int] = defaultdict(int)
        self.start_time = time.time()

    def record_request(self, provider: str, response_time: float, success: bool):
        self.total_requests[provider] += 1
        self.response_times[provider].append(response_time)

        if len(self.response_times[provider]) > 100:
            self.response_times[provider] = self.response_times[provider][-100:]

        if not success:
            self.error_counts[provider] += 1

    def get_metrics(self, provider: str) -> Dict[str, Any]:
        times = self.response_times[provider]
        total = self.total_requests[provider]
        errors = self.error_counts[provider]

        if not times:
            return {
                "avg_response_time": 0,
                "min_response_time": 0,
                "max_response_time": 0,
                "p95_response_time": 0,
                "error_rate": 0,
                "total_requests": total,
                "error_count": errors,
            }

        return {
            "avg_response_time": round(statistics.mean(times), 2),
            "min_response_time": round(min(times), 2),
            "max_response_time": round(max(times), 2),
            "p95_response_time": (
                round(statistics.quantiles(times, n=20)[-1], 2)
                if len(times) > 20
                else round(max(times), 2)
            ),
            "error_rate": round((errors / total * 100) if total > 0 else 0, 2),
            "total_requests": total,
            "error_count": errors,
        }


circuit_breakers: Dict[str, CircuitBreaker] = {}
performance_metrics = PerformanceMetrics()


def calculate_health_score(
    status: Dict[str, Any], metrics: Dict[str, Any], cb: CircuitBreaker
) -> float:
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
