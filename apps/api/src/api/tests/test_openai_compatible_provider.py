from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from api.providers.openai_compatible import OpenAICompatibleProvider


def _provider(**config_overrides) -> OpenAICompatibleProvider:
    config = {
        "endpoint": "https://provider.test",
        "api_key_env": "TEST_PROVIDER_API_KEY",
        "default_model": "test-model",
    }
    config.update(config_overrides)
    return OpenAICompatibleProvider("provider", config)


class TestInvoke:
    @pytest.mark.asyncio
    async def test_strips_tools_when_provider_disables_openai_tools(self):
        provider = _provider(supports_openai_tools=False)

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await provider.invoke(
                messages=[{"role": "user", "content": "hello"}],
                tools=[{"type": "function", "function": {"name": "test_tool"}}],
                tool_choice="auto",
                parallel_tool_calls=True,
            )

        assert result.ok is True
        sent_body = instance.post.await_args.kwargs["json"]
        assert "tools" not in sent_body
        assert "tool_choice" not in sent_body
        assert "parallel_tool_calls" not in sent_body

    @pytest.mark.asyncio
    async def test_http_error_includes_response_body(self):
        provider = _provider()

        mock_response = MagicMock(status_code=400)
        mock_response.text = '{"error":{"message":"Tool schema invalid"}}'
        http_error = httpx.HTTPStatusError(
            "400 Bad Request",
            request=MagicMock(),
            response=mock_response,
        )

        with patch("httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_response)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance
            mock_response.raise_for_status.side_effect = http_error

            result = await provider.invoke(
                messages=[{"role": "user", "content": "hello"}],
            )

        assert result.ok is False
        assert "HTTP 400" in result.error
        assert "Tool schema invalid" in result.error
