"""
Generic provider implementation for Cloudflare-like endpoints.
"""

from typing import AsyncGenerator, Dict, Any, Union
from .base import BaseProvider


class GenericProvider(BaseProvider):
    """Generic provider for custom or Cloudflare-like endpoints."""

    async def invoke(
        self, prompt: str, stream: bool = False, model: str = "generic-model", **kwargs
    ) -> Union[AsyncGenerator[Dict[str, Any], None], Dict[str, Any]]:
        """Invoke generic API endpoint."""
        headers = {
            "Content-Type": "application/json",
        }

        # Add API key to headers if available
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = self.endpoint.rstrip("/") + (self.invoke_path or "/")

        # Use the raw payload passed in kwargs, or build a simple one
        payload = kwargs.get(
            "payload",
            {
                "model": model,
                "prompt": prompt,
                "max_tokens": kwargs.get("max_tokens", 512),
                "temperature": kwargs.get("temperature", 0.2),
            },
        )

        result = await self._make_request(
            url, payload, headers, kwargs.get("timeout_ms", 30000), stream=False
        )

        if isinstance(result, dict):
            if not result.get("ok", False):
                return result

            # Try to extract text from various response formats
            data = result["result"]

            # Try different response formats
            text = ""
            if isinstance(data, dict):
                # Try OpenAI-style
                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    text = choice.get("message", {}).get("content", "") or choice.get(
                        "text", ""
                    )
                # Try simple text field
                elif "text" in data:
                    text = data["text"]
                # Try response field
                elif "response" in data:
                    text = data["response"]
                # Try content field
                elif "content" in data:
                    text = data["content"]
                # Fallback to string representation
                else:
                    text = str(data)
            else:
                text = str(data)

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
