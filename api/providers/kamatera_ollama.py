"""
Kamatera Ollama provider implementation.
Handles communication with Ollama API running on Kamatera Server 2 (192.175.23.150:8002).
"""

from typing import AsyncGenerator, Dict, Any, Union
import json
import httpx
from .base import BaseProvider


class KamateraOllamaProvider(BaseProvider):
    """Kamatera Ollama API provider for Server 2 (192.175.23.150:8002)."""

    async def invoke(
        self, prompt: str, stream: bool = False, model: str = "phi3:latest", **kwargs
    ) -> Union[AsyncGenerator[Dict[str, Any], None], Dict[str, Any]]:
        """Invoke Kamatera Ollama API."""
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
                "top_p": kwargs.get("top_p", 0.9),
            },
        }

        if stream:
            result = await self._make_request(
                url, payload, headers, kwargs.get("timeout_ms", 30000), stream=True
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
                url, payload, headers, kwargs.get("timeout_ms", 30000), stream=False
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

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Kamatera Ollama server."""
        try:
            # Check if server is reachable
            health_url = self.endpoint.rstrip("/") + "/health"
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                if response.status_code == 200:
                    return {"status": "healthy", "endpoint": health_url}
                else:
                    return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def list_models(self) -> Dict[str, Any]:
        """List available models on Kamatera Ollama server."""
        try:
            models_url = self.endpoint.rstrip("/") + "/api/tags"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(models_url)
                if response.status_code == 200:
                    data = response.json()
                    models = [model["name"] for model in data.get("models", [])]
                    return {
                        "ok": True,
                        "models": models,
                        "count": len(models),
                    }
                else:
                    return {"ok": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}