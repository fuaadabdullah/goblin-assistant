"""
SiliconeFlow provider implementation.
SiliconeFlow provides high-performance AI inference with competitive pricing.
"""

from typing import AsyncGenerator, Dict, Any, Union
import json
import httpx
from .base import BaseProvider


class SiliconeFlowProvider(BaseProvider):
    """SiliconeFlow API provider."""

    async def invoke(
        self,
        prompt: str,
        stream: bool = False,
        model: str = "Qwen/Qwen2.5-7B-Instruct",
        **kwargs,
    ) -> Union[AsyncGenerator[Dict[str, Any], None], Dict[str, Any]]:
        """Invoke SiliconeFlow API."""
        if not self.api_key:
            return {
                "ok": False,
                "error": "missing-siliconeflow-key",
                "latency_ms": 0,
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # SiliconeFlow uses OpenAI-compatible API
        url = f"{self.endpoint.rstrip('/')}/v1/chat/completions"

        # Build request payload
        messages = kwargs.get("messages", [])
        if not messages:
            # If no messages provided, create from prompt
            messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 512),
            "temperature": kwargs.get("temperature", 0.7),
            "stream": stream,
        }

        # Add optional parameters
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "frequency_penalty" in kwargs:
            payload["frequency_penalty"] = kwargs["frequency_penalty"]
        if "presence_penalty" in kwargs:
            payload["presence_penalty"] = kwargs["presence_penalty"]

        try:
            import time

            start = time.perf_counter()

            async with httpx.AsyncClient(timeout=kwargs.get("timeout", 30.0)) as client:
                result = await client.post(url, json=payload, headers=headers)
                result.raise_for_status()

            elapsed_ms = (time.perf_counter() - start) * 1000

            if stream:
                # Return streaming generator
                return self._stream_response(result)
            else:
                # Parse non-streaming response
                data = result.json()

                # Extract text from response
                choices = data.get("choices", [])
                if not choices:
                    return {
                        "ok": False,
                        "error": "no-choices-in-response",
                        "latency_ms": elapsed_ms,
                    }

                text = choices[0].get("message", {}).get("content", "")

                return {
                    "ok": True,
                    "result": {"text": text, "raw": data},
                    "model": data.get("model", model),
                    "provider": "siliconeflow",
                    "latency_ms": elapsed_ms,
                }

        except httpx.HTTPStatusError as e:
            return {
                "ok": False,
                "error": f"http-{e.response.status_code}",
                "details": str(e),
                "latency_ms": 0,
            }
        except Exception as e:
            return {
                "ok": False,
                "error": "request-failed",
                "details": str(e),
                "latency_ms": 0,
            }

    async def _stream_response(
        self, response: httpx.Response
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Parse streaming response from SiliconeFlow."""
        try:
            async for line in response.aiter_lines():
                if not line.strip():
                    continue

                # Remove "data: " prefix
                if line.startswith("data: "):
                    line = line[6:]

                # Check for end of stream
                if line.strip() == "[DONE]":
                    break

                try:
                    data = json.loads(line)
                    choices = data.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield {
                                "ok": True,
                                "text": content,
                                "provider": "siliconeflow",
                                "done": False,
                            }
                except json.JSONDecodeError:
                    continue

            # Send final done message
            yield {"ok": True, "text": "", "provider": "siliconeflow", "done": True}

        except Exception as e:
            yield {
                "ok": False,
                "error": "stream-error",
                "details": str(e),
                "provider": "siliconeflow",
            }

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "SiliconeFlowProvider":
        """Create provider instance from configuration."""
        # BaseProvider expects a config dict, so just pass it through
        return cls(config)
