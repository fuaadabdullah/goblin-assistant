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
_COST_TABLE: Dict[str, Dict[str, float]] = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "o1": {"input": 0.015, "output": 0.06},
    "o1-mini": {"input": 0.003, "output": 0.012},
    "o3-mini": {"input": 0.0011, "output": 0.0044},
}


class OpenAIProvider(BaseProvider):
    COST_INPUT_PER_1K = 0.005
    COST_OUTPUT_PER_1K = 0.015

    def __init__(
        self,
        provider_id: str | Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(provider_id, config)
        self._api_key = os.getenv(self.config.get("api_key_env", "OPENAI_API_KEY"), "").strip()
        self._base_url = (self.endpoint or _ENDPOINT).rstrip("/")
        self.endpoint = self._base_url

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _model_cost(self, model: str) -> Dict[str, float]:
        for key, costs in _COST_TABLE.items():
            if key in model:
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
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
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
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._base_url}/models",
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
