"""Health Score tests for ProviderDispatcher routing."""

from api.ops.circuit_breaker import CircuitBreaker, calculate_health_score


class TestCalculateHealthScore:
    """Tests for ``calculate_health_score()`` in ops circuit breaker."""

    def test_healthy_provider_scores_near_100(self):
        status = {"status": "healthy"}
        metrics = {"error_rate": 0, "avg_response_time": 100}
        cb = CircuitBreaker()
        score = calculate_health_score(status, metrics, cb)
        assert score == 100.0

    def test_open_breaker_penalizes_score(self):
        status = {"status": "healthy"}
        metrics = {"error_rate": 0, "avg_response_time": 100}
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        cb.record_failure()
        score = calculate_health_score(status, metrics, cb)
        assert score <= 60.0  # 100 - 40 (OPEN)

    def test_half_open_breaker_penalizes_less(self):
        status = {"status": "healthy"}
        metrics = {"error_rate": 0, "avg_response_time": 100}
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        cb.state = "HALF_OPEN"
        score = calculate_health_score(status, metrics, cb)
        assert score == 80.0  # 100 - 20 (HALF_OPEN)

    def test_high_error_rate_penalizes_score(self):
        status = {"status": "healthy"}
        metrics = {"error_rate": 15, "avg_response_time": 100}
        cb = CircuitBreaker()
        score = calculate_health_score(status, metrics, cb)
        assert score == 80.0  # 100 - 20 (error_rate > 10)

    def test_high_latency_penalizes_score(self):
        status = {"status": "healthy"}
        metrics = {"error_rate": 0, "avg_response_time": 6000}
        cb = CircuitBreaker()
        score = calculate_health_score(status, metrics, cb)
        assert score == 90.0  # 100 - 10 (avg_response_time > 5000)

    def test_combined_penalties_stack(self):
        status = {"status": "unhealthy"}
        metrics = {"error_rate": 6, "avg_response_time": 3000}
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        cb.record_failure()
        score = calculate_health_score(status, metrics, cb)
        # 100 - 30 (unhealthy) - 40 (OPEN) - 10 (error_rate > 5) - 5 (latency > 2000)
        assert score == 15.0

    def test_score_minimum_zero(self):
        status = {"status": "unhealthy"}
        metrics = {"error_rate": 100, "avg_response_time": 10000}
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        cb.record_failure()
        score = calculate_health_score(status, metrics, cb)
        assert score >= 0.0
