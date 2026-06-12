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


class AnthropicProvider(BaseProvider):
    def __init__(
        self,
        provider_id: str | Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(provider_id, config)
        api_key_env = self.config.get("api_key_env") or "ANTHROPIC_API_KEY"
        self._api_key = os.getenv(str(api_key_env), "").strip()
        self._base_url = (self.endpoint or _ENDPOINT).rstrip("/")
        self.endpoint = self._base_url

    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": _API_VERSION,
            "Content-Type": "application/json",
        }

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
            cost = self.estimate_cost(
                int(usage.get("input_tokens", 0)),
                int(usage.get("output_tokens", 0)),
                model=model_name,
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

        async with (
            httpx.AsyncClient(timeout=120) as client,
            client.stream(
                "POST",
                f"{self._base_url}/v1/messages",
                headers=self._headers(),
                json=body,
            ) as resp,
        ):
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
            from .base import is_billing_error

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._base_url}/v1/models",
                    headers=self._headers(),
                )
            latency = (time.perf_counter() - t0) * 1000
            ok = resp.status_code == 200
            billing = not ok and is_billing_error(resp.status_code, resp.text)
            return ProviderHealth(
                self.provider_id,
                ok,
                latency_ms=latency,
                error=None if ok else f"HTTP {resp.status_code}",
                billing_issue=billing,
            )
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000
            return ProviderHealth(
                self.provider_id,
                False,
                latency_ms=latency,
                error=str(exc),
            )
