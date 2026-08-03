"""Focused tests for redundant provider-pool health aggregation."""

from api.health import _summarize_provider_health


def test_provider_health_warns_when_redundant_provider_fails() -> None:
    status = _summarize_provider_health(
        {
            "openai": {"status": "unhealthy", "configured": True},
            "gemini": {"status": "healthy", "configured": True},
        }
    )

    assert status == "warnings"


def test_provider_health_degrades_without_healthy_provider() -> None:
    status = _summarize_provider_health(
        {
            "openai": {"status": "unhealthy", "configured": True},
            "gemini": {"status": "degraded", "configured": True},
        }
    )

    assert status == "degraded"


def test_provider_health_degrades_when_only_unknown_and_unhealthy_remain() -> None:
    status = _summarize_provider_health(
        {
            "openai": {"status": "unhealthy", "configured": True},
            "gemini": {"status": "unknown", "configured": True},
        }
    )

    assert status == "degraded"


def test_provider_health_warns_when_a_configured_provider_cannot_serve() -> None:
    status = _summarize_provider_health(
        {
            "openai": {"status": "healthy", "configured": True},
            "anthropic": {"status": "billing_issue", "configured": True},
            "azure_openai": {"status": "unknown", "configured": False},
        }
    )

    assert status == "warnings"


def test_provider_health_ignores_unconfigured_providers() -> None:
    status = _summarize_provider_health(
        {
            "openai": {"status": "healthy", "configured": True},
            "anthropic": {"status": "unknown", "configured": False},
        }
    )

    assert status == "healthy"
