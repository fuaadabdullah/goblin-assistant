"""Disposable Colab worker provider with dual API compatibility.

Supports:
- OpenAI-compatible endpoints: /v1/chat/completions and /v1/models
- Custom worker endpoints: /chat and /health
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
import structlog

from .base import BaseProvider, ProviderHealth, ProviderResult

logger = structlog.get_logger(__name__)

_OPENAI_UNSUPPORTED_STATUS = {404, 405, 422, 501}


class ColabWorkerProvider(BaseProvider):
    COST_INPUT_PER_1K = 0.0
    COST_OUTPUT_PER_1K = 0.0

    def __init__(
        self,
        provider_id: str | Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(provider_id, config)
        endpoint_env = str(self.config.get("endpoint_env", "COLAB_WORKER_ENDPOINT"))
        self._base_url = os.getenv(endpoint_env, self.endpoint).strip().rstrip("/")
        self.endpoint = self._base_url

        api_key_env = str(self.config.get("api_key_env", "COLAB_WORKER_API_KEY"))
        self._api_key = os.getenv(api_key_env, "").strip()

        self._openai_path = str(self.config.get("openai_invoke_path", "/v1/chat/completions"))
        self._custom_chat_path = str(self.config.get("invoke_path", "/chat"))
        self._health_path = str(self.config.get("health_path", "/health"))
        self._models_path = str(self.config.get("models_path", "/v1/models"))

    def _with_leading_slash(self, path: str) -> str:
        normalized = path.strip()
        if not normalized:
            return "/"
        if not normalized.startswith("/"):
            return f"/{normalized}"
        return normalized

    def _url(self, path: str) -> str:
        return f"{self._base_url}{self._with_leading_slash(path)}"

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _prompt_from_messages(
        self,
        normalized_messages: List[Dict[str, str]],
        prompt: str,
    ) -> str:
        if prompt:
            return prompt
        for message in reversed(normalized_messages):
            content = str(message.get("content", "")).strip()
            if content:
                return content
        return ""

    def _format_http_error(self, exc: httpx.HTTPStatusError) -> str:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        response_text = ""
        if exc.response is not None:
            try:
                response_text = exc.response.text.strip()
            except (AttributeError, TypeError, ValueError):
                response_text = ""
        if response_text:
            compact = " ".join(response_text.split())
            if len(compact) > 400:
                compact = f"{compact[:397]}..."
            return f"HTTP {status_code}: {compact}"
        return str(exc)

    def _extract_text_and_usage(self, data: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content:
                    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
                    return content, usage
        response_text = data.get("response")
        if isinstance(response_text, str):
            usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
            return response_text, usage
        raise ValueError("No response text found in worker payload")

    async def _invoke_openai(
        self,
        *,
        normalized_messages: List[Dict[str, str]],
        model_name: str,
        max_tokens: int,
        temperature: float,
        prompt: str,
        **kwargs: Any,
    ) -> ProviderResult:
        body = {
            "model": model_name,
            "messages": normalized_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }
        body.pop("stream", None)
        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                self._url(self._openai_path),
                headers=self._headers(),
                json=body,
            )
        latency = (time.perf_counter() - t0) * 1000
        resp.raise_for_status()
        data = resp.json()
        text, usage = self._extract_text_and_usage(data)
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

    async def _invoke_custom(
        self,
        *,
        normalized_messages: List[Dict[str, str]],
        model_name: str,
        max_tokens: int,
        temperature: float,
        prompt: str,
        **kwargs: Any,
    ) -> ProviderResult:
        custom_kwargs = dict(kwargs)
        custom_kwargs.pop("tools", None)
        custom_kwargs.pop("tool_choice", None)
        custom_kwargs.pop("parallel_tool_calls", None)
        prompt_text = self._prompt_from_messages(normalized_messages, prompt)
        body = {
            "prompt": prompt_text,
            "messages": normalized_messages,
            "model": model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **custom_kwargs,
        }
        body.pop("stream", None)
        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                self._url(self._custom_chat_path),
                headers=self._headers(),
                json=body,
            )
        latency = (time.perf_counter() - t0) * 1000
        resp.raise_for_status()
        data = resp.json()
        text, usage = self._extract_text_and_usage(data)
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
        model_name = model or self.default_model or "gemma-3-12b"
        if not self._base_url:
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=model_name,
                error="Colab worker endpoint not configured",
            )
        if stream:
            kwargs["stream"] = True

        try:
            return await self._invoke_openai(
                normalized_messages=normalized_messages,
                model_name=model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                prompt=prompt,
                **kwargs,
            )
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in _OPENAI_UNSUPPORTED_STATUS:
                try:
                    return await self._invoke_custom(
                        normalized_messages=normalized_messages,
                        model_name=model_name,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        prompt=prompt,
                        **kwargs,
                    )
                except Exception as custom_exc:
                    error_message = str(custom_exc)
                    self.record_failure(error_message)
                    return ProviderResult(
                        ok=False,
                        provider=self.provider_id,
                        model=model_name,
                        error=error_message,
                    )

            error_message = self._format_http_error(exc)
            self.record_failure(error_message)
            logger.warning(
                "colab_worker_invoke_failed",
                provider=self.provider_id,
                status_code=status,
                error=error_message,
            )
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=model_name,
                error=error_message,
            )
        except (
            httpx.HTTPError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ) as exc:
            error_message = str(exc)
            self.record_failure(error_message)
            logger.warning(
                "colab_worker_invoke_failed",
                provider=self.provider_id,
                error=error_message,
            )
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=model_name,
                error=error_message,
            )

    def stream(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        prompt: str = "",
        **kwargs: Any,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        async def _stream() -> AsyncGenerator[Dict[str, Any], None]:
            normalized_messages = self.normalize_messages(messages, prompt=prompt, **kwargs)
            model_name = model or self.default_model or "gemma-3-12b"
            body = {
                "model": model_name,
                "messages": normalized_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
                **kwargs,
            }
            async with httpx.AsyncClient(timeout=180) as client:
                try:
                    async with client.stream(
                        "POST",
                        self._url(self._openai_path),
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
                    return
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code if exc.response is not None else None
                    if status not in _OPENAI_UNSUPPORTED_STATUS:
                        raise
                except httpx.HTTPError:
                    pass

            fallback = await self.invoke(
                messages=normalized_messages,
                model=model_name,
                stream=False,
                max_tokens=max_tokens,
                temperature=temperature,
                prompt=prompt,
                **kwargs,
            )
            if not fallback.ok:
                raise RuntimeError(fallback.error or "custom /chat fallback failed")
            if fallback.text:
                yield {"text": fallback.text}

        return _stream()

    async def health_check(self) -> ProviderHealth:
        if not self._base_url:
            return ProviderHealth(self.provider_id, False, error="No endpoint")

        t0 = time.perf_counter()
        primary_error: Optional[str] = None
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self._url(self._health_path), headers=self._headers())
            latency = (time.perf_counter() - t0) * 1000
            if resp.status_code < 400:
                healthy = True
                try:
                    payload = resp.json()
                    if isinstance(payload, dict) and "healthy" in payload:
                        healthy = bool(payload.get("healthy"))
                except ValueError:
                    healthy = True
                return ProviderHealth(
                    self.provider_id,
                    healthy,
                    latency_ms=latency,
                    error=None if healthy else "health payload reported unhealthy",
                )
            primary_error = f"HTTP {resp.status_code}"
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            primary_error = str(exc)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                fallback = await client.get(self._url(self._models_path), headers=self._headers())
            latency = (time.perf_counter() - t0) * 1000
            healthy = fallback.status_code < 400
            return ProviderHealth(
                self.provider_id,
                healthy,
                latency_ms=latency,
                error=None if healthy else (primary_error or f"HTTP {fallback.status_code}"),
            )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            latency = (time.perf_counter() - t0) * 1000
            error = primary_error or str(exc)
            if primary_error and str(exc) != primary_error:
                error = f"{primary_error}; fallback probe failed: {exc}"
            return ProviderHealth(
                self.provider_id,
                False,
                latency_ms=latency,
                error=error,
            )
