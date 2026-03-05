"""
LlamaCPP provider implementation for local and remote LlamaCPP servers.
"""

from typing import AsyncGenerator, Dict, Any, Union
import json
import httpx
from .base import BaseProvider


class LlamaCPPProvider(BaseProvider):
    """LlamaCPP API provider (local and remote)."""

    async def invoke(
        self, prompt: str, stream: bool = False, model: str = "local-model", **kwargs
    ) -> Union[AsyncGenerator[Dict[str, Any], None], Dict[str, Any]]:
        """Invoke LlamaCPP API."""
        headers = {
            "Content-Type": "application/json",
        }

        url = self.endpoint.rstrip("/") + (self.invoke_path or "/v1/chat/completions")

        # Build OpenAI-compatible payload for LlamaCPP
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens", 512),
            "temperature": kwargs.get("temperature", 0.2),
        }

        if stream:
            payload["stream"] = True
            result = await self._make_request(
                url, payload, headers, kwargs.get("timeout_ms", 60000), stream=True
            )

            if isinstance(result, dict) and not result.get("ok", False):
                return result

            # Return streaming generator
            async def gen():
                async for data in self._stream_sse_response(result):
                    try:
                        parsed = json.loads(data)
                        if "choices" in parsed and parsed["choices"]:
                            choice = parsed["choices"][0]
                            delta = choice.get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield {"text": content, "raw": parsed}
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

                # Extract text from OpenAI-style response
                data = result["result"]
                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    text = choice.get("message", {}).get("content", "") or choice.get(
                        "text", ""
                    )

                    # Check for garbled output (common with corrupted models)
                    garbled_chars = [
                        "\x1c",
                        "\x00",
                        "\x01",
                        "\x02",
                        "\x03",
                        "\x04",
                        "\x05",
                        "\x06",
                        "\x07",
                        "\x08",
                        "\x0b",
                        "\x0c",
                        "\x0e",
                        "\x0f",
                        "\x10",
                        "\x11",
                        "\x12",
                        "\x13",
                        "\x14",
                        "\x15",
                        "\x16",
                        "\x17",
                        "\x18",
                        "\x19",
                        "\x1a",
                        "\x1b",
                        "\x1d",
                        "\x1e",
                        "\x1f",
                    ]
                    garbled_ratio = (
                        sum(1 for char in text if char in garbled_chars) / len(text)
                        if text
                        else 0
                    )

                    if garbled_ratio > 0.1:
                        return {
                            "ok": False,
                            "error": f"llamacpp-garbled-output: Model produced {garbled_ratio:.1%} garbled characters. Try a different model.",
                            "latency_ms": result["latency_ms"],
                        }

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

    async def _stream_sse_response(
        self, resp: httpx.Response
    ) -> AsyncGenerator[str, None]:
        """Parse SSE response from LlamaCPP."""
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
