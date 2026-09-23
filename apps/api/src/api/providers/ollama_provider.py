"""Ollama provider backed by the official ollama-python AsyncClient."""

from __future__ import annotations

import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import ollama
import structlog

from .base import BaseProvider, ProviderHealth, ProviderResult

logger = structlog.get_logger(__name__)

# OpenAI-style kwargs that map onto Ollama's native `options` object.
_OPTION_ALIASES = {
    "top_p": "top_p",
    "top_k": "top_k",
    "seed": "seed",
    "stop": "stop",
    "num_predict": "num_predict",
    "num_ctx": "num_ctx",
}


def _value(response: Any, key: str, default: Any = None) -> Any:
    """Read a field from either a typed ollama response or a plain dict."""
    if isinstance(response, dict):
        return response.get(key, default)
    return getattr(response, key, default)


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
        self._client = ollama.AsyncClient(host=self._base_url or None)

    def _options(
        self, max_tokens: int, temperature: float, kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        options: Dict[str, Any] = {
            "num_predict": max_tokens,
            "temperature": temperature,
        }
        for key, value in kwargs.items():
            if key in _OPTION_ALIASES and value is not None:
                options[_OPTION_ALIASES[key]] = value
        return options

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
        if not self._base_url:
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=model_name,
                error="Ollama endpoint not configured",
            )

        t0 = time.perf_counter()
        try:
            response = await self._client.chat(
                model=model_name,
                messages=normalized_messages,
                stream=False,
                options=self._options(max_tokens, temperature, kwargs),
            )
            latency = (time.perf_counter() - t0) * 1000
            text = str(_value(_value(response, "message"), "content") or "").strip()
            if not text:
                raise ValueError("Empty response content — check Ollama model and endpoint config")
            usage = {
                "prompt_tokens": _value(response, "prompt_eval_count", 0) or 0,
                "completion_tokens": _value(response, "eval_count", 0) or 0,
            }
            raw = {
                "choices": [{"message": {"role": "assistant", "content": text}}],
                "usage": usage,
            }
            self.record_success()
            return ProviderResult(
                ok=True,
                text=text,
                raw=raw,
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
        async for chunk in await self._client.chat(
            model=model_name,
            messages=normalized_messages,
            stream=True,
            options=self._options(max_tokens, temperature, kwargs),
        ):
            text = str(_value(_value(chunk, "message"), "content") or "")
            if text:
                yield {"text": text}
            if _value(chunk, "done", False):
                break

    async def health_check(self) -> ProviderHealth:
        if not self._base_url:
            return ProviderHealth(self.provider_id, False, error="No endpoint")
        t0 = time.perf_counter()
        try:
            await self._client.list()
            latency = (time.perf_counter() - t0) * 1000
            return ProviderHealth(
                self.provider_id,
                True,
                latency_ms=latency,
                error=None,
            )
        except Exception as exc:
            latency = (time.perf_counter() - t0) * 1000
            return ProviderHealth(
                self.provider_id,
                False,
                latency_ms=latency,
                error=str(exc),
            )
