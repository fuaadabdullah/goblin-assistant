"""
Groq provider implementation.
"""

from typing import AsyncGenerator, Dict, Any, Union
from .base import BaseProvider


class GroqProvider(BaseProvider):
    """Groq API provider."""

    async def invoke(
        self,
        prompt: str,
        stream: bool = False,
        model: str = "llama-3.1-8b-instant",
        **kwargs,
    ) -> Union[AsyncGenerator[Dict[str, Any], None], Dict[str, Any]]:
        """Invoke Groq API."""
        if not self.api_key:
            return {
                "ok": False,
                "error": "missing-groq-key",
                "latency_ms": 0,
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = self.endpoint.rstrip("/") + (self.invoke_path or "/v1/chat/completions")

        # Build request payload — use conversation messages if provided, else single prompt
        messages = kwargs.get("messages", [{"role": "user", "content": prompt}])
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 512),
            "temperature": kwargs.get("temperature", 0.2),
        }

        # Groq doesn't support streaming in the same way, so we use non-streaming
        result = await self._make_request(
            url, payload, headers, kwargs.get("timeout_ms", 30000), stream=False
        )

        if isinstance(result, dict):
            if not result.get("ok", False):
                return result

            # Extract text from Groq response (similar to OpenAI format)
            data = result["result"]
            if "choices" in data and data["choices"]:
                choice = data["choices"][0]
                text = choice.get("message", {}).get("content", "") or choice.get(
                    "text", ""
                )

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
