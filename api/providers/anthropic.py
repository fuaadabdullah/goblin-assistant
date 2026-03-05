"""
Anthropic Claude provider implementation.
"""

from typing import AsyncGenerator, Dict, Any, Union
from .base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API provider."""

    async def invoke(
        self,
        prompt: str,
        stream: bool = False,
        model: str = "claude-3-sonnet-20240229",
        **kwargs,
    ) -> Union[AsyncGenerator[Dict[str, Any], None], Dict[str, Any]]:
        """Invoke Anthropic Claude API."""
        if not self.api_key:
            return {
                "ok": False,
                "error": "missing-anthropic-key",
                "latency_ms": 0,
            }

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        url = self.endpoint.rstrip("/") + (self.invoke_path or "/v1/messages")

        # Build request payload in Anthropic format
        payload = {
            "model": model,
            "max_tokens": kwargs.get("max_tokens", 512),
            "temperature": kwargs.get("temperature", 0.2),
            "messages": [{"role": "user", "content": prompt}],
        }

        if stream:
            payload["stream"] = True
            # Note: Anthropic streaming implementation would go here
            # For now, fall back to non-streaming
            result = await self._make_request(
                url, payload, headers, kwargs.get("timeout_ms", 30000), stream=False
            )
        else:
            result = await self._make_request(
                url, payload, headers, kwargs.get("timeout_ms", 30000), stream=False
            )

        if isinstance(result, dict):
            if not result.get("ok", False):
                return result

            # Extract text from Anthropic response
            data = result["result"]
            if "content" in data and data["content"]:
                # Anthropic returns content as array of text blocks
                text = ""
                for block in data["content"]:
                    if block.get("type") == "text":
                        text += block.get("text", "")

                return {
                    "ok": True,
                    "result": {"text": text, "raw": data},
                    "latency_ms": result["latency_ms"],
                }

        return {
            "ok": False,
            "error": "invalid-response-format",
            "latency_ms": 0,
        }
