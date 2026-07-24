"""Provider Errors tests for chat_router."""

from .conftest import (
    pytest,
)


class TestRaiseStructuredProviderError:
    """Tests for _raise_structured_provider_error helper."""

    def test_auth_error(self):
        """Test auth error handling."""
        from api.chat_router import _raise_structured_provider_error
        from api.providers.base import ProviderErrorCategory

        with pytest.raises(Exception) as exc_info:
            _raise_structured_provider_error(
                {
                    "error": "Invalid API key",
                    "error_category": ProviderErrorCategory.AUTH.value,
                    "provider": "openai",
                }
            )

        assert exc_info.value.status_code == 401

    def test_rate_limit_error(self):
        """Test rate limit error handling."""
        from api.chat_router import _raise_structured_provider_error
        from api.providers.base import ProviderErrorCategory

        with pytest.raises(Exception) as exc_info:
            _raise_structured_provider_error(
                {
                    "error": "Rate limited",
                    "error_category": ProviderErrorCategory.RATE_LIMIT.value,
                    "provider": "openai",
                }
            )

        assert exc_info.value.status_code == 429

    def test_timeout_error(self):
        """Test timeout error handling."""
        from api.chat_router import _raise_structured_provider_error
        from api.providers.base import ProviderErrorCategory

        with pytest.raises(Exception) as exc_info:
            _raise_structured_provider_error(
                {
                    "error": "Request timeout",
                    "error_category": ProviderErrorCategory.TIMEOUT.value,
                    "provider": "openai",
                }
            )

        assert exc_info.value.status_code == 504

    def test_model_error(self):
        """Test model error handling."""
        from api.chat_router import _raise_structured_provider_error
        from api.providers.base import ProviderErrorCategory

        with pytest.raises(Exception) as exc_info:
            _raise_structured_provider_error(
                {
                    "error": "Model not found",
                    "error_category": ProviderErrorCategory.MODEL_ERROR.value,
                    "provider": "openai",
                }
            )

        assert exc_info.value.status_code == 400
