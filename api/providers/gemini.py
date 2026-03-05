"""
Google Gemini provider implementation.
"""

from typing import AsyncGenerator, Dict, Any, Union
from .base import BaseProvider


class GeminiProvider(BaseProvider):
    """Google Gemini API provider."""

    async def invoke(
        self, prompt: str, stream: bool = False, model: str = "gemini-2.0-flash", **kwargs
    ) -> Union[AsyncGenerator[Dict[str, Any], None], Dict[str, Any]]:
        """Invoke Google Gemini API."""
        if not self.api_key:
            return {
                "ok": False,
                "error": "missing-gemini-key",
                "latency_ms": 0,
            }

        headers = {
            "Content-Type": "application/json",
        }

        # Gemini uses a different URL structure
        url = f"{self.endpoint.rstrip('/')}/v1beta/models/{model}:generateContent?key={self.api_key}"

        # Build request payload for Gemini
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": kwargs.get("max_tokens", 512),
                "temperature": kwargs.get("temperature", 0.2),
            },
        }

        # Gemini doesn't support streaming in the same way, so we use non-streaming
        result = await self._make_request(
            url, payload, headers, kwargs.get("timeout_ms", 30000), stream=False
        )

        if isinstance(result, dict):
            if not result.get("ok", False):
                return result

            # Extract text from Gemini response
            data = result["result"]
            if "candidates" in data and data["candidates"]:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    text = ""
                    for part in candidate["content"]["parts"]:
                        text += part.get("text", "")

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
