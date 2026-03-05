"""
Azure OpenAI provider implementation.

Azure OpenAI uses a different URL format and auth header than standard OpenAI:
- URL: {endpoint}/openai/deployments/{deployment_id}/chat/completions?api-version={version}
- Auth: api-key header (not Bearer token)
"""

import os
import json
from typing import AsyncGenerator, Dict, Any, Union
import httpx
from .base import BaseProvider


class AzureOpenAIProvider(BaseProvider):
    """Azure OpenAI API provider."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.azure_endpoint = os.getenv(
            "AZURE_OPENAI_ENDPOINT", config.get("endpoint", "")
        ).rstrip("/")
        self.api_version = os.getenv(
            "AZURE_API_VERSION", config.get("api_version", "2024-05-01-preview")
        )
        self.default_deployment = os.getenv(
            "AZURE_DEPLOYMENT_ID", config.get("default_deployment", "gpt-4o-mini")
        )
        # Azure uses AZURE_API_KEY env var
        self.api_key = os.getenv("AZURE_API_KEY", "")

    def _get_deployment(self, model: str) -> str:
        """Map model name to Azure deployment ID."""
        deployment_map = {
            "gpt-4o-mini": "gpt-4o-mini",
            "gpt-4o": "gpt-4o",
            "gpt-4": "gpt-4",
            "gpt-4.1": "gpt-4.1",
            "gpt-4-turbo": "gpt-4-turbo",
            "gpt-35-turbo": "gpt-35-turbo",
        }
        return deployment_map.get(model, self.default_deployment)

    async def invoke(
        self,
        prompt: str,
        stream: bool = False,
        model: str = "gpt-4o-mini",
        **kwargs,
    ) -> Union[AsyncGenerator[Dict[str, Any], None], Dict[str, Any]]:
        """Invoke Azure OpenAI API."""
        if not self.api_key:
            return {"ok": False, "error": "missing-azure-key", "latency_ms": 0}

        deployment = self._get_deployment(model)
        url = (
            f"{self.azure_endpoint}/openai/deployments/{deployment}"
            f"/chat/completions?api-version={self.api_version}"
        )

        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

        messages = kwargs.get("messages", [])
        if not messages:
            messages = [{"role": "user", "content": prompt}]

        payload = {
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

                data = result["result"]
                if "choices" in data and data["choices"]:
                    text = data["choices"][0].get("message", {}).get("content", "")
                    return {
                        "ok": True,
                        "result": {"text": text, "raw": data},
                        "provider": "azure",
                        "model": model,
                        "latency_ms": result["latency_ms"],
                    }

            return {"ok": False, "error": "invalid-response-format", "latency_ms": 0}

    async def _stream_sse_response(
        self, resp: httpx.Response
    ) -> AsyncGenerator[str, None]:
        """Parse SSE response from Azure OpenAI."""
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
                        data = s[len("data:"):].strip()
                        if data:
                            yield data
