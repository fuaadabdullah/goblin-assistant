"""Azure OpenAI provider."""

from __future__ import annotations

import json
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import httpx
import structlog

from .base import BaseProvider, ProviderHealth, ProviderResult

logger = structlog.get_logger(__name__)


class AzureOpenAIProvider(BaseProvider):
    COST_INPUT_PER_1K = 0.005
    COST_OUTPUT_PER_1K = 0.015

    def __init__(
        self,
        provider_id: str | Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(provider_id, config)
        self._api_key = os.getenv(self.config.get("api_key_env", "AZURE_API_KEY"), "").strip()
        self._endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", self.endpoint).rstrip("/")
        self._api_version = os.getenv(
            "AZURE_API_VERSION",
            str(self.config.get("api_version", "2024-05-01-preview")),
        )
        self._deployment = os.getenv(
            "AZURE_DEPLOYMENT_ID",
            str(
                self.config.get("deployment_id")
                or self.config.get("default_deployment")
                or self.default_model
            ),
        )
        self.endpoint = self._endpoint

    def _headers(self) -> Dict[str, str]:
        return {
            "api-key": self._api_key,
            "Content-Type": "application/json",
        }

    def _url(self, deployment: str) -> str:
        return (
            f"{self._endpoint}/openai/deployments/{deployment}"
            f"/chat/completions?api-version={self._api_version}"
        )

    def _is_configured(self) -> bool:
        return bool(self._api_key and self._endpoint and self._deployment)

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
        deployment = model or self._deployment
        if not self._is_configured():
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=deployment,
                error=(
                    "Azure OpenAI not fully configured "
                    "(AZURE_API_KEY / AZURE_OPENAI_ENDPOINT / AZURE_DEPLOYMENT_ID)"
                ),
            )

        body = {
            "messages": normalized_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(
                    self._url(deployment),
                    headers=self._headers(),
                    json=body,
                )
            latency = (time.perf_counter() - t0) * 1000
            resp.raise_for_status()
            data = resp.json()

            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            cost = self.estimate_cost(
                int(usage.get("prompt_tokens", 0)),
                int(usage.get("completion_tokens", 0)),
            )
            self.record_success()
            return ProviderResult(
                ok=True,
                text=text,
                raw=data,
                provider=self.provider_id,
                model=deployment,
                usage=usage,
                cost_usd=cost,
                latency_ms=latency,
            )
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000
            self.record_failure(str(exc))
            logger.warning("azure_invoke_failed", error=str(exc))
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=deployment,
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
        deployment = model or self._deployment
        body = {
            "messages": normalized_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                self._url(deployment),
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
        if not self._is_configured():
            return ProviderHealth(self.provider_id, False, error="Not configured")
        t0 = time.perf_counter()
        try:
            body = {"messages": [{"role": "user", "content": "ping"}], "max_tokens": 1}
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    self._url(self._deployment),
                    headers=self._headers(),
                    json=body,
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

    async def embed(
        self,
        texts: Union[str, List[str]],
        model: str = "",
        **kwargs: Any,
    ) -> Union[List[float], List[List[float]]]:
        if not self._is_configured():
            raise ValueError("Azure OpenAI embeddings not configured")

        deployment = model or self._deployment
        is_single = isinstance(texts, str)
        inputs = [texts] if is_single else texts
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                (
                    f"{self._endpoint}/openai/deployments/{deployment}/embeddings"
                    f"?api-version={self._api_version}"
                ),
                headers=self._headers(),
                json={"input": inputs},
            )
        resp.raise_for_status()
        data = resp.json()
        embeddings = [item["embedding"] for item in data.get("data", [])]
        return embeddings[0] if is_single else embeddings
