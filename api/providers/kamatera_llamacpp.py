"""
Kamatera llama.cpp provider implementation.
Handles communication with the router API running on Kamatera Server 1 (45.61.51.220:8000).

This is the primary LLM provider for Goblin Assistant chat functionality.
Uses OpenAI-compatible chat completions API.
"""

from typing import Dict, Any
import httpx
from .base import BaseProvider


class KamateraLlamaCppProvider(BaseProvider):
    """
    Kamatera llama.cpp provider for Server 1 Router API (45.61.51.220:8000).

    Primary chat provider for Goblin Assistant.
    Supports OpenAI-compatible chat completions with qwen2.5 model.
    """

    async def invoke(
        self, prompt: str, stream: bool = False, model: str = "qwen2.5:latest", **kwargs
    ) -> Dict[str, Any]:
        """
        Invoke Kamatera llama.cpp Router API.

        Args:
            prompt: User input prompt
            stream: Streaming not supported (will be ignored)
            model: Model name (default: qwen2.5:latest)
            **kwargs: Additional parameters (max_tokens, temperature, top_p, timeout_ms)

        Returns:
            Dict with 'ok' status, 'result' (contains 'text' and 'raw'), and 'latency_ms'
        """
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,  # Include API key for Router API authentication
        }

        url = self.endpoint.rstrip("/") + (self.invoke_path or "/v1/chat/completions")

        # Build OpenAI-compatible payload for Router API
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens", 512),
            "temperature": kwargs.get("temperature", 0.2),
            "top_p": kwargs.get("top_p", 0.9),
        }

        # Note: Streaming not supported due to inference server limitations
        # All requests use non-streaming for reliability
        if stream:
            import sys

            print(
                "⚠️  Streaming not supported by Kamatera llama.cpp - using non-streaming mode",
                file=sys.stderr,
            )

        # Make non-streaming request to Router API
        result = await self._make_request(
            url, payload, headers, kwargs.get("timeout_ms", 30000), stream=False
        )

        # Validate and parse response
        if not isinstance(result, dict):
            return {
                "ok": False,
                "error": "invalid-response-type",
                "latency_ms": 0,
            }

        if not result.get("ok", False):
            return result

        # Extract response text from OpenAI-style format
        data = result.get("result", {})
        if not isinstance(data, dict) or "choices" not in data:
            return {
                "ok": False,
                "error": "missing-choices-field",
                "latency_ms": result.get("latency_ms", 0),
            }

        choices = data.get("choices", [])
        if not choices or not isinstance(choices, list):
            return {
                "ok": False,
                "error": "empty-choices",
                "latency_ms": result.get("latency_ms", 0),
            }

        # Get first choice's content
        choice = choices[0]
        if not isinstance(choice, dict):
            return {
                "ok": False,
                "error": "invalid-choice-format",
                "latency_ms": result.get("latency_ms", 0),
            }

        # Extract text from message or fallback to text field
        message = choice.get("message", {})
        if isinstance(message, dict):
            text = message.get("content", "")
        else:
            text = choice.get("text", "")

        if not isinstance(text, str):
            return {
                "ok": False,
                "error": "invalid-text-format",
                "latency_ms": result.get("latency_ms", 0),
            }

        return {
            "ok": True,
            "result": {"text": text, "raw": data},
            "provider": "llamacpp_kamatera",
            "model": model,
            "latency_ms": result.get("latency_ms", 0),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Kamatera Router API."""
        try:
            # Check if server is reachable
            health_url = self.endpoint.rstrip("/") + "/health"
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                if response.status_code == 200:
                    return {"status": "healthy", "endpoint": health_url}
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status_code}",
                    }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def list_models(self) -> Dict[str, Any]:
        """List available models on Kamatera Router API."""
        try:
            models_url = self.endpoint.rstrip("/") + "/v1/models"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(models_url)
                if response.status_code == 200:
                    data = response.json()
                    models = [model["id"] for model in data.get("data", [])]
                    return {
                        "ok": True,
                        "models": models,
                        "count": len(models),
                    }
                else:
                    return {"ok": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
