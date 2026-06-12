import time
from collections import deque
from typing import Optional

from .models import MetricReliability


def assess_reliability(history: deque, timestamp: float) -> MetricReliability:
    """Assess reliability of a metric based on freshness and history completeness."""
    if not history:
        return MetricReliability.UNKNOWN

    time_diff = time.time() - timestamp
    if time_diff > 300:
        return MetricReliability.POOR
    elif time_diff > 60:
        return MetricReliability.FAIR
    elif time_diff > 10:
        return MetricReliability.GOOD

    recent_count = sum(1 for h in history if time.time() - h["timestamp"] < 60)
    if recent_count >= 5:
        return MetricReliability.EXCELLENT
    elif recent_count >= 2:
        return MetricReliability.GOOD
    else:
        return MetricReliability.FAIR


def calculate_trend(history: deque, window_minutes: int = 10) -> Optional[str]:
    """Calculate trend direction using linear regression over recent history."""
    cutoff = time.time() - (window_minutes * 60)
    recent_values = [h["value"] for h in history if h["timestamp"] > cutoff]

    if len(recent_values) < 3:
        return None

    n = len(recent_values)
    x_values = list(range(n))
    y_values = recent_values

    x_mean = sum(x_values) / n
    y_mean = sum(y_values) / n

    numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
    denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return "stable"

    slope = numerator / denominator
    if abs(slope) < 0.01:
        return "stable"
    return "increasing" if slope > 0 else "decreasing"
