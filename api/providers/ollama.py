"""
Ollama local provider implementation.
"""

from typing import AsyncGenerator, Dict, Any, Union
import json
import httpx
from .base import BaseProvider


class OllamaProvider(BaseProvider):
    """Ollama local API provider."""

    async def invoke(
        self, prompt: str, stream: bool = False, model: str = "llama2", **kwargs
    ) -> Union[AsyncGenerator[Dict[str, Any], None], Dict[str, Any]]:
        """Invoke Ollama API."""
        headers = {
            "Content-Type": "application/json",
        }

        url = self.endpoint.rstrip("/") + (self.invoke_path or "/api/generate")

        # Build request payload for Ollama
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "num_predict": kwargs.get("max_tokens", 512),
                "temperature": kwargs.get("temperature", 0.2),
            },
        }

        if stream:
            result = await self._make_request(
                url, payload, headers, kwargs.get("timeout_ms", 60000), stream=True
            )

            if isinstance(result, dict) and not result.get("ok", False):
                return result

            # Return streaming generator for Ollama
            async def gen():
                async for data in self._stream_ollama_response(result):
                    try:
                        parsed = json.loads(data)
                        response = parsed.get("response", "")
                        if response:
                            yield {"text": response, "raw": parsed}
                        if parsed.get("done", False):
                            break
                    except Exception:
                        continue

            return {"ok": True, "stream": gen(), "latency_ms": 0}
        else:
            result = await self._make_request(
                url, payload, headers, kwargs.get("timeout_ms", 60000), stream=False
            )

            if isinstance(result, dict):
                if not result.get("ok", False):
                    return result

                # Extract text from Ollama response
                data = result["result"]
                text = data.get("response", "")

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

    async def _stream_ollama_response(
        self, resp: httpx.Response
    ) -> AsyncGenerator[str, None]:
        """Parse streaming response from Ollama."""
        async for chunk in resp.aiter_bytes():
            lines = chunk.split(b"\n")
            for line in lines:
                line = line.strip()
                if line:
                    yield line.decode(errors="ignore")
