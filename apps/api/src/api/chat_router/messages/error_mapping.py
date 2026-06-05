"""Pure functions for mapping provider-error categories to HTTP codes and error codes."""

from ...providers.base import ProviderErrorCategory


def provider_error_status_code(category: str) -> int:
    """Map a provider error category to an appropriate HTTP status code."""
    if category == ProviderErrorCategory.AUTH.value:
        return 401
    if category == ProviderErrorCategory.RATE_LIMIT.value:
        return 429
    if category == ProviderErrorCategory.TIMEOUT.value:
        return 504
    if category == ProviderErrorCategory.MODEL_ERROR.value:
        return 400
    if category in {
        ProviderErrorCategory.SERVER_ERROR.value,
        ProviderErrorCategory.CONNECTION.value,
    }:
        return 503
    return 502


def provider_error_code(category: str) -> str:
    """Map a provider error category to a machine-readable error code string."""
    if category == ProviderErrorCategory.AUTH.value:
        return "AUTHENTICATION_REQUIRED"
    if category == ProviderErrorCategory.RATE_LIMIT.value:
        return "CHAT_RATE_LIMITED"
    if category == ProviderErrorCategory.TIMEOUT.value:
        return "CHAT_TIMEOUT"
    if category == ProviderErrorCategory.MODEL_ERROR.value:
        return "CHAT_PROVIDER_UNAVAILABLE"
    if category in {
        ProviderErrorCategory.SERVER_ERROR.value,
        ProviderErrorCategory.CONNECTION.value,
    }:
        return "CHAT_BACKEND_UNAVAILABLE"
    return "CHAT_PROVIDER_ERROR"