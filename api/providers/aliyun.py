"""
Aliyun DashScope provider implementation.

DashScope provides an OpenAI-compatible API:
- URL: https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions (international)
- Auth: Bearer token with DASHSCOPE_API_KEY
- Models: qwen-turbo, qwen-plus, qwen-max, qwen-long, etc.
"""

import os
from typing import AsyncGenerator, Dict, Any, Union
from .base import BaseProvider


class AliyunProvider(BaseProvider):
    """Aliyun DashScope provider (OpenAI-compatible)."""

    DEFAULT_ENDPOINT = os.getenv(
        "DASHSCOPE_ENDPOINT", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    )

    MODEL_MAP = {
        "qwen-turbo": "qwen-turbo",
        "qwen-plus": "qwen-plus",
        "qwen-max": "qwen-max",
        "qwen-long": "qwen-long",
        "qwen2.5-7b-instruct": "qwen2.5-7b-instruct",
    }

    def __init__(self, config: Dict[str, Any]):
        config.setdefault("api_key_env", "DASHSCOPE_API_KEY")
        config.setdefault("endpoint", self.DEFAULT_ENDPOINT)
        super().__init__(config)
        self.dashscope_endpoint = self.endpoint.rstrip("/")
        self.default_model = config.get("default_model", "qwen-turbo")

    async def invoke(
        self,
        prompt: str,
        stream: bool = False,
        model: str = "qwen-turbo",
        **kwargs,
    ) -> Union[AsyncGenerator[Dict[str, Any], None], Dict[str, Any]]:
        """Invoke DashScope OpenAI-compatible API."""
        api_key = self._get_api_key()
        if not api_key:
            return {"ok": False, "error": "missing-dashscope-api-key", "latency_ms": 0}

        url = f"{self.dashscope_endpoint}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        messages = kwargs.get("messages", [])
        if not messages:
            messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 512),
            "temperature": kwargs.get("temperature", 0.7),
            "stream": stream,
        }

        result = await self._make_request(
            url, payload, headers, kwargs.get("timeout_ms", 30000), stream=stream
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
                    "provider": "aliyun",
                    "model": model,
                    "latency_ms": result["latency_ms"],
                }

        return {"ok": False, "error": "invalid-response-format", "latency_ms": 0}
