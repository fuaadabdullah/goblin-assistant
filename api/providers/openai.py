"""
OpenAI provider implementation.
"""

from typing import AsyncGenerator, Dict, Any, Union, List
import json
import httpx
from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    """OpenAI API provider."""

    async def invoke(
        self, prompt: str, stream: bool = False, model: str = "gpt-3.5-turbo", **kwargs
    ) -> Union[AsyncGenerator[Dict[str, Any], None], Dict[str, Any]]:
        """Invoke OpenAI API."""
        if not self.api_key:
            return {
                "ok": False,
                "error": "missing-openai-key",
                "latency_ms": 0,
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Use standard OpenAI Chat Completions API
        base = self.endpoint.rstrip("/")
        if not base.endswith("/v1"):
            base = base.rstrip("/") + "/v1"
        url = base + "/chat/completions"
        # Build request payload for Chat Completions API
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

        if stream:
            result = await self._make_request(
                url, payload, headers, kwargs.get("timeout_ms", 30000), stream=True
            )

            if isinstance(result, dict) and not result.get("ok", False):
                return result

            # Return streaming generator
            async def gen():
                async for data in self._stream_sse_response(result):
                    if data == "[DONE]":
                        break
                    try:
                        parsed = json.loads(data)
                        if "choices" in parsed and parsed["choices"]:
                            delta = parsed["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield {"text": delta["content"], "raw": parsed}
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

                # Extract text from OpenAI response
                data = result["result"]
                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    text = choice.get("message", {}).get("content", "")
                    return {
                        "ok": True,
                        "result": {"text": text, "raw": data},
                        "provider": "openai",
                        "model": model,
                        "latency_ms": result["latency_ms"],
                    }

            return {
                "ok": False,
                "error": "invalid-response-format",
                "latency_ms": 0,
            }

    async def embed(
        self,
        texts: Union[str, List[str]],
        model: str = "text-embedding-3-small",
        **kwargs,
    ) -> Union[List[float], List[List[float]]]:
        """Generate embeddings using OpenAI API."""
        if not self.api_key:
            raise ValueError("OpenAI API key is required for embeddings")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Properly construct URL for embeddings
        base = self.endpoint.rstrip("/")
        if not base.endswith("/v1"):
            base = base.rstrip("/") + "/v1"
        url = base + "/embeddings"

        # Handle single text or list of texts
        is_single = isinstance(texts, str)
        if is_single:
            texts = [texts]

        # Build request payload
        payload = {
            "model": model,
            "input": texts,
        }

        result = await self._make_request(
            url, payload, headers, kwargs.get("timeout_ms", 30000), stream=False
        )

        if isinstance(result, dict) and result.get("ok"):
            data = result["result"]
            if "data" in data:
                embeddings = [item["embedding"] for item in data["data"]]
                return embeddings[0] if is_single else embeddings

        raise Exception(f"Embedding failed: {result.get('error', 'Unknown error')}")

    async def _stream_sse_response(
        self, resp: httpx.Response
    ) -> AsyncGenerator[str, None]:
        """Parse SSE response from OpenAI."""
        async for chunk in resp.aiter_bytes():
            parts = chunk.split(b"\n\n")
            for p in parts:
                line = p.strip()
                if not line:
                    continue
                lines = line.split(b"\n")
                for L in lines:
                    s = L.decode(errors="ignore").strip()
                    if s.startswith("data:"):
                        data = s[len("data:") :].strip()
                        if data:
                            yield data
