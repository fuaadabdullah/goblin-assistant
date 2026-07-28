from typing import Any, Dict, List


def get_provider_capabilities(provider_settings: list, provider_name: str) -> List[str]:
    for provider in provider_settings:
        if provider["name"] == provider_name:
            return provider.get("capabilities", [])
    return []


def get_provider_priority(provider_settings: list, provider_name: str) -> int:
    for provider in provider_settings:
        if provider["name"] == provider_name:
            return provider.get("priority_tier", 0)
    return 0


def calculate_provider_health_score(provider_metrics: Dict[str, Any]) -> float:
    """Weighted health score: 70% availability, 30% reliability."""
    if not provider_metrics:
        return 50.0

    import statistics

    healthy_count = sum(1 for p in provider_metrics.values() if p["status"] == "healthy")
    base_score = (healthy_count / len(provider_metrics)) * 100

    reliability_scores = [
        (
            100
            if p["reliability"] == "excellent"
            else (75 if p["reliability"] == "good" else 50 if p["reliability"] == "fair" else 25)
        )
        for p in provider_metrics.values()
    ]
    reliability_score = statistics.mean(reliability_scores) if reliability_scores else 50

    return (base_score * 0.7) + (reliability_score * 0.3)
