"""Focused tests for redundant provider-pool health aggregation."""

from api.health import _summarize_provider_health


def test_provider_health_warns_when_redundant_provider_fails() -> None:
    status = _summarize_provider_health(
        {
            "openai": {"status": "unhealthy"},
            "gemini": {"status": "healthy"},
        }
    )

    assert status == "warnings"


def test_provider_health_degrades_without_healthy_provider() -> None:
    status = _summarize_provider_health(
        {
            "openai": {"status": "unhealthy"},
            "gemini": {"status": "degraded"},
        }
    )

    assert status == "degraded"


def test_provider_health_accepts_non_failing_provider_states() -> None:
    status = _summarize_provider_health(
        {
            "openai": {"status": "healthy"},
            "anthropic": {"status": "billing_issue"},
            "azure_openai": {"status": "unknown"},
        }
    )

    assert status == "healthy"
