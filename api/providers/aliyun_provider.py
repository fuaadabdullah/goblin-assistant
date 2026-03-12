"""Aliyun DashScope provider."""

from __future__ import annotations

import json
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
import structlog

from .base import BaseProvider, ProviderHealth, ProviderResult

logger = structlog.get_logger(__name__)

_DEFAULT_ENDPOINT = "https://dashscope-intl.aliyuncs.com/compatible-mode"
_COST_TABLE: Dict[str, Dict[str, float]] = {
    "qwen-max": {"input": 0.004, "output": 0.012},
    "qwen-plus": {"input": 0.0008, "output": 0.002},
    "qwen-turbo": {"input": 0.0002, "output": 0.0006},
    "qwen2.5-72b": {"input": 0.0009, "output": 0.0009},
    "qwen2.5-32b": {"input": 0.00045, "output": 0.00045},
    "qwen2.5-14b": {"input": 0.00023, "output": 0.00023},
    "qwen2.5-7b": {"input": 0.0001, "output": 0.0001},
}


class AliyunProvider(BaseProvider):
    COST_INPUT_PER_1K = 0.0008
    COST_OUTPUT_PER_1K = 0.002

    def __init__(
        self,
        provider_id: str | Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(provider_id, config)
        self._api_key = os.getenv(self.config.get("api_key_env", "DASHSCOPE_API_KEY"), "").strip()
        self._base_url = os.getenv(
            "DASHSCOPE_ENDPOINT",
            self.endpoint or _DEFAULT_ENDPOINT,
        ).rstrip("/")
        self.endpoint = self._base_url

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _model_cost(self, model: str) -> Dict[str, float]:
        lowered = model.lower()
        for key, costs in _COST_TABLE.items():
            if key in lowered:
                return costs
        return {"input": self.COST_INPUT_PER_1K, "output": self.COST_OUTPUT_PER_1K}

    async def invoke(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        *,
        stream: bool = False,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        prompt: str = "",
        **kwargs: Any,
    ) -> ProviderResult:
        normalized_messages = self.normalize_messages(messages, prompt=prompt, **kwargs)
        model_name = model or self.default_model or "qwen-plus"
        if not self._api_key:
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=model_name,
                error="DASHSCOPE_API_KEY not set",
            )

        body = {
            "model": model_name,
            "messages": normalized_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/chat/completions",
                    headers=self._headers(),
                    json=body,
                )
            latency = (time.perf_counter() - t0) * 1000
            resp.raise_for_status()
            data = resp.json()

            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            costs = self._model_cost(model_name)
            cost = (
                int(usage.get("prompt_tokens", 0)) * costs["input"] / 1000
                + int(usage.get("completion_tokens", 0)) * costs["output"] / 1000
            )
            self.record_success()
            return ProviderResult(
                ok=True,
                text=text,
                raw=data,
                provider=self.provider_id,
                model=model_name,
                usage=usage,
                cost_usd=cost,
                latency_ms=latency,
            )
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000
            self.record_failure(str(exc))
            logger.warning("aliyun_invoke_failed", error=str(exc))
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=model_name,
                latency_ms=latency,
                error=str(exc),
            )

    async def stream(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        prompt: str = "",
        **kwargs: Any,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        normalized_messages = self.normalize_messages(messages, prompt=prompt, **kwargs)
        model_name = model or self.default_model or "qwen-plus"
        body = {
            "model": model_name,
            "messages": normalized_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/v1/chat/completions",
                headers=self._headers(),
                json=body,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield {"text": delta}

    async def health_check(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(self.provider_id, False, error="No API key")
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{self._base_url}/v1/models",
                    headers=self._headers(),
                )
            latency = (time.perf_counter() - t0) * 1000
            return ProviderHealth(
                self.provider_id,
                resp.status_code < 400,
                latency_ms=latency,
                error=None if resp.status_code < 400 else f"HTTP {resp.status_code}",
            )
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000
            return ProviderHealth(
                self.provider_id,
                False,
                latency_ms=latency,
                error=str(exc),
            )
