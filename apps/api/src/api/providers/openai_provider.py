"""OpenAI provider."""

from __future__ import annotations

import json
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import httpx
import structlog

from .base import BaseProvider, ProviderHealth, ProviderResult

logger = structlog.get_logger(__name__)

_ENDPOINT = "https://api.openai.com/v1"


class OpenAIProvider(BaseProvider):
    def __init__(
        self,
        provider_id: str | Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(provider_id, config)
        api_key_env = self.config.get("api_key_env") or "OPENAI_API_KEY"
        self._api_key = os.getenv(str(api_key_env), "").strip()
        self._base_url = (self.endpoint or _ENDPOINT).rstrip("/")
        self.endpoint = self._base_url

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

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
        model_name = model or self.default_model or "gpt-4o-mini"
        if not self._api_key:
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=model_name,
                error="OPENAI_API_KEY not set",
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
                    f"{self._base_url}/chat/completions",
                    headers=self._headers(),
                    json=body,
                )
            latency = (time.perf_counter() - t0) * 1000
            resp.raise_for_status()
            data = resp.json()

            text = data["choices"][0]["message"].get("content") or ""
            usage = data.get("usage", {})
            cost = self.estimate_cost(
                int(usage.get("prompt_tokens", 0)),
                int(usage.get("completion_tokens", 0)),
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
            logger.warning("openai_invoke_failed", error=str(exc))
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
        model_name = model or self.default_model or "gpt-4o-mini"
        body = {
            "model": model_name,
            "messages": normalized_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }
        async with httpx.AsyncClient(timeout=120) as client, client.stream(
            "POST",
            f"{self._base_url}/chat/completions",
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
            from .base import is_billing_error

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._base_url}/models",
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

    async def embed(
        self,
        texts: Union[str, List[str]],
        model: str = "text-embedding-3-small",
        **kwargs: Any,
    ) -> Union[List[float], List[List[float]]]:
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY not set")

        is_single = isinstance(texts, str)
        inputs = [texts] if is_single else texts
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self._base_url}/embeddings",
                headers=self._headers(),
                json={"model": model, "input": inputs},
            )
        resp.raise_for_status()
        data = resp.json()
        embeddings = [item["embedding"] for item in data.get("data", [])]
        return embeddings[0] if is_single else embeddings
