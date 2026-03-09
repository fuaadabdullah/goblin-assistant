"""llama.cpp provider."""

from __future__ import annotations

import json
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
import structlog

from .base import BaseProvider, ProviderHealth, ProviderResult

logger = structlog.get_logger(__name__)


class LlamaCPPProvider(BaseProvider):
    COST_INPUT_PER_1K = 0.0
    COST_OUTPUT_PER_1K = 0.0

    def __init__(
        self,
        provider_id: str | Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(provider_id, config)
        env_key = str(self.config.get("endpoint_env", "LLAMACPP_GCP_ENDPOINT"))
        self._base_url = os.getenv(env_key, self.endpoint).rstrip("/")
        self.endpoint = self._base_url

    def _headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}

    async def _resolve_model(self) -> str:
        if self.default_model:
            return self.default_model
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._base_url}/v1/models")
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                if models:
                    return models[0].get("id", "default")
        except Exception:
            pass
        return "default"

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
        if not self._base_url:
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=model or "unknown",
                error="LlamaCPP endpoint not configured",
            )

        model_name = model or await self._resolve_model()
        body = {
            "model": model_name,
            "messages": normalized_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
            **kwargs,
        }
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=120) as client:
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
            self.record_success()
            return ProviderResult(
                ok=True,
                text=text,
                raw=data,
                provider=self.provider_id,
                model=model_name,
                usage=usage,
                cost_usd=0.0,
                latency_ms=latency,
            )
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000
            self.record_failure(str(exc))
            logger.warning(
                "llamacpp_invoke_failed",
                provider=self.provider_id,
                error=str(exc),
            )
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
        model_name = model or await self._resolve_model()
        body = {
            "model": model_name,
            "messages": normalized_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }
        async with httpx.AsyncClient(timeout=180) as client:
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
        if not self._base_url:
            return ProviderHealth(self.provider_id, False, error="No endpoint")
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(f"{self._base_url}/health")
            latency = (time.perf_counter() - t0) * 1000
            ok = resp.status_code == 200 and resp.json().get("status") == "ok"
            return ProviderHealth(
                self.provider_id,
                ok,
                latency_ms=latency,
                error=None if ok else f"HTTP {resp.status_code}",
            )
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000
            return ProviderHealth(
                self.provider_id,
                False,
                latency_ms=latency,
                error=str(exc),
            )
