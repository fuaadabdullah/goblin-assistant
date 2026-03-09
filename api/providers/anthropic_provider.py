"""Anthropic provider."""

from __future__ import annotations

import json
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
import structlog

from .base import BaseProvider, ProviderHealth, ProviderResult

logger = structlog.get_logger(__name__)

_ENDPOINT = "https://api.anthropic.com"
_API_VERSION = "2023-06-01"
_COST_TABLE: Dict[str, Dict[str, float]] = {
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku": {"input": 0.0008, "output": 0.004},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
}


class AnthropicProvider(BaseProvider):
    COST_INPUT_PER_1K = 0.003
    COST_OUTPUT_PER_1K = 0.015

    def __init__(
        self,
        provider_id: str | Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(provider_id, config)
        self._api_key = os.getenv(self.config.get("api_key_env", "ANTHROPIC_API_KEY"), "").strip()
        self._base_url = (self.endpoint or _ENDPOINT).rstrip("/")
        self.endpoint = self._base_url

    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": _API_VERSION,
            "Content-Type": "application/json",
        }

    def _model_cost(self, model: str) -> Dict[str, float]:
        for key, costs in _COST_TABLE.items():
            if key in model:
                return costs
        return {"input": self.COST_INPUT_PER_1K, "output": self.COST_OUTPUT_PER_1K}

    def _split_messages(
        self,
        messages: List[Dict[str, str]],
    ) -> tuple[Optional[str], List[Dict[str, str]]]:
        system = None
        chat: List[Dict[str, str]] = []
        for item in messages:
            if item.get("role") == "system":
                system = item.get("content", "")
            else:
                chat.append(item)
        return system, chat

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
        model_name = model or self.default_model or "claude-3-5-haiku-latest"
        if not self._api_key:
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=model_name,
                error="ANTHROPIC_API_KEY not set",
            )

        system, chat = self._split_messages(normalized_messages)
        body: Dict[str, Any] = {
            "model": model_name,
            "messages": chat,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }
        if system:
            body["system"] = system

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/messages",
                    headers=self._headers(),
                    json=body,
                )
            latency = (time.perf_counter() - t0) * 1000
            resp.raise_for_status()
            data = resp.json()

            text = "".join(
                block.get("text", "")
                for block in data.get("content", [])
                if block.get("type") == "text"
            )
            usage = data.get("usage", {})
            costs = self._model_cost(model_name)
            cost = (
                int(usage.get("input_tokens", 0)) * costs["input"] / 1000
                + int(usage.get("output_tokens", 0)) * costs["output"] / 1000
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
            logger.warning("anthropic_invoke_failed", error=str(exc))
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
        model_name = model or self.default_model or "claude-3-5-haiku-latest"
        system, chat = self._split_messages(normalized_messages)
        body: Dict[str, Any] = {
            "model": model_name,
            "messages": chat,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }
        if system:
            body["system"] = system

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/v1/messages",
                headers=self._headers(),
                json=body,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:].strip()
                    try:
                        event = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") == "content_block_delta":
                        delta = event.get("delta", {}).get("text", "")
                        if delta:
                            yield {"text": delta}

    async def health_check(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(self.provider_id, False, error="No API key")
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._base_url}/v1/models",
                    headers=self._headers(),
                )
            latency = (time.perf_counter() - t0) * 1000
            return ProviderHealth(
                self.provider_id,
                resp.status_code == 200,
                latency_ms=latency,
                error=None if resp.status_code == 200 else f"HTTP {resp.status_code}",
            )
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000
            return ProviderHealth(
                self.provider_id,
                False,
                latency_ms=latency,
                error=str(exc),
            )
