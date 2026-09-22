"""Ollama provider backed by the official ollama-python async client."""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Mapping
from typing import Any, AsyncGenerator, Dict, List, Optional

import structlog
from ollama import AsyncClient

from .base import BaseProvider, ProviderHealth, ProviderResult
from .retry import retry_provider_call

logger = structlog.get_logger(__name__)

_CHAT_KWARGS = ("format", "tools", "keep_alive", "think")


def _response_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(exclude_none=True)
        if isinstance(dumped, dict):
            return dumped

    try:
        return dict(value)
    except (TypeError, ValueError):
        return {}


class OllamaProvider(BaseProvider):
    def __init__(
        self,
        provider_id: str | Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(provider_id, config)
        env_key = str(self.config.get("endpoint_env", ""))
        raw_url = os.getenv(env_key, self.endpoint).rstrip("/")
        if raw_url and not raw_url.startswith(("http://", "https://")):
            raw_url = f"http://{raw_url}"
        self._base_url = raw_url
        self.endpoint = self._base_url
        self._ollama_client = (
            AsyncClient(host=self._base_url, timeout=180.0) if self._base_url else None
        )

    @staticmethod
    def _options(
        max_tokens: int,
        temperature: float,
        kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        options: Dict[str, Any] = {
            "num_predict": max_tokens,
            "temperature": temperature,
        }
        extra_options = kwargs.get("options")
        if isinstance(extra_options, Mapping):
            options.update(extra_options)
        return options

    @staticmethod
    def _chat_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
        return {key: kwargs[key] for key in _CHAT_KWARGS if key in kwargs}

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
        model_name = model or self.default_model or "qwen2.5:3b"
        if self._ollama_client is None:
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=model_name,
                error="Ollama endpoint not configured",
            )

        options = self._options(max_tokens, temperature, kwargs)
        chat_kwargs = self._chat_kwargs(kwargs)
        t0 = time.perf_counter()
        try:
            response = await retry_provider_call(
                lambda: self._ollama_client.chat(
                    model=model_name,
                    messages=normalized_messages,
                    stream=False,
                    options=options,
                    **chat_kwargs,
                )
            )
            latency = (time.perf_counter() - t0) * 1000
            data = _response_dict(response)
            text = str(data.get("message", {}).get("content", "") or "")
            if not text:
                raise ValueError("Empty response content — check Ollama model and endpoint config")

            prompt_tokens = int(data.get("prompt_eval_count") or 0)
            completion_tokens = int(data.get("eval_count") or 0)
            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
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
            error_msg = str(exc) or f"{type(exc).__name__}: (no message)"
            self.record_failure(error_msg)
            logger.warning(
                "ollama_invoke_failed",
                provider=self.provider_id,
                error=error_msg,
            )
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=model_name,
                latency_ms=latency,
                error=error_msg,
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
        model_name = model or self.default_model or "qwen2.5:3b"
        if self._ollama_client is None:
            raise RuntimeError("Ollama endpoint not configured")

        options = self._options(max_tokens, temperature, kwargs)
        chat_kwargs = self._chat_kwargs(kwargs)
        response_stream = await retry_provider_call(
            lambda: self._ollama_client.chat(
                model=model_name,
                messages=normalized_messages,
                stream=True,
                options=options,
                **chat_kwargs,
            )
        )

        async for response in response_stream:
            data = _response_dict(response)
            text = str(data.get("message", {}).get("content", "") or "")
            if text:
                yield {"text": text}
            if data.get("done"):
                break

    async def health_check(self) -> ProviderHealth:
        if self._ollama_client is None:
            return ProviderHealth(self.provider_id, False, error="No endpoint")

        t0 = time.perf_counter()
        try:
            async with asyncio.timeout(10):
                await retry_provider_call(self._ollama_client.list)
            latency = (time.perf_counter() - t0) * 1000
            return ProviderHealth(
                self.provider_id,
                True,
                latency_ms=latency,
            )
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000
            return ProviderHealth(
                self.provider_id,
                False,
                latency_ms=latency,
                error=str(exc),
            )
