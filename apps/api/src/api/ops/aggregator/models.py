from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class MetricReliability(Enum):
    """Reliability levels for metrics based on data freshness and completeness"""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNKNOWN = "unknown"


@dataclass
class AggregatedMetric:
    """Normalized metric with reliability and metadata"""

    name: str
    value: float
    unit: str
    reliability: MetricReliability
    timestamp: float
    source: str
    description: str
    trend: Optional[str] = None  # "increasing", "decreasing", "stable"


@dataclass
class SystemHealth:
    """Comprehensive system health with trend analysis"""

    overall_score: float
    status: str  # "healthy", "degraded", "critical"
    components: Dict[str, float]
    trend: str
    last_updated: float
    reliability: MetricReliability
