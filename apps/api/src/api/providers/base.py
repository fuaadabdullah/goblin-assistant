"""
Base provider abstraction for Goblin Assistant.

All provider implementations share the same response model, circuit breaker,
and compatibility helpers so callers can keep using the legacy dispatcher
contract while the internals use a stricter typed core.
"""

from __future__ import annotations

import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import httpx

from .contracts import ProviderCapabilityMatrix
from .pricing import resolve_model_pricing


class ProviderErrorCategory(str, Enum):
    """Structured error categories for provider failures."""

    AUTH = "auth"  # 401/403, invalid API key
    RATE_LIMIT = "rate-limit"  # 429, quota exceeded
    TIMEOUT = "timeout"  # Connection/read timeout
    MODEL_ERROR = "model-error"  # Invalid model, context too long
    SERVER_ERROR = "server-error"  # 5xx from provider
    CONNECTION = "connection"  # DNS, network, connection refused
    UNKNOWN = "unknown"


class ProviderCircuitState(str, Enum):
    """Provider-local circuit breaker states used by routing."""

    CLOSED = "closed"
    SOFT_OPEN = "soft_open"
    HARD_OPEN = "hard_open"


def classify_provider_error(error: Union[str, Exception]) -> ProviderErrorCategory:
    """Classify a provider error into a structured category."""
    msg = str(error).lower()

    if any(
        kw in msg
        for kw in (
            "401",
            "403",
            "unauthorized",
            "forbidden",
            "invalid api key",
            "invalid_api_key",
            "authentication",
        )
    ):
        return ProviderErrorCategory.AUTH

    if any(kw in msg for kw in ("429", "rate limit", "rate_limit", "quota", "too many requests")):
        return ProviderErrorCategory.RATE_LIMIT

    if any(kw in msg for kw in ("timeout", "timed out", "deadline exceeded")):
        return ProviderErrorCategory.TIMEOUT

    if any(
        kw in msg
        for kw in (
            "model not found",
            "invalid model",
            "context_length_exceeded",
            "context length",
            "max_tokens",
        )
    ):
        return ProviderErrorCategory.MODEL_ERROR

    if re.search(r"\b5\d{2}\b", msg) or any(
        kw in msg for kw in ("internal server error", "bad gateway", "service unavailable")
    ):
        return ProviderErrorCategory.SERVER_ERROR

    if any(
        kw in msg
        for kw in (
            "connection refused",
            "dns",
            "name resolution",
            "unreachable",
            "connection error",
            "connect error",
        )
    ):
        return ProviderErrorCategory.CONNECTION

    return ProviderErrorCategory.UNKNOWN


@dataclass
class ProviderResult:
    """Normalized provider response with dict-like compatibility helpers."""

    ok: bool
    text: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)
    provider: str = ""
    model: str = ""
    usage: Dict[str, Any] = field(default_factory=dict)
    cost_usd: Optional[float] = None
    latency_ms: float = 0.0
    error: Optional[str] = None
    error_category: Optional[str] = None  # ProviderErrorCategory value

    def _compat_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "text": self.text,
            "raw": self.raw,
            "provider": self.provider,
            "model": self.model,
            "usage": self.usage,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "error_category": self.error_category,
            "result": {
                "text": self.text,
                "raw": self.raw,
                "usage": self.usage,
                "cost_usd": self.cost_usd,
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "ok": self.ok,
            "result": {
                "text": self.text,
                "raw": self.raw,
                "usage": self.usage,
                "cost_usd": self.cost_usd,
            },
            "provider": self.provider,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }
        if self.error_category:
            d["error_category"] = self.error_category
        return d

    def get(self, key: str, default: Any = None) -> Any:
        return self._compat_dict().get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._compat_dict()[key]

    def __contains__(self, key: object) -> bool:
        return key in self._compat_dict()


_BILLING_PHRASES = (
    "billing",
    "credit balance is too low",
    "exceeded your current quota",
    "subscription is disabled",
    "readonlydisabledsubscription",
    "payment required",
    "insufficient_quota",
)


def is_billing_error(status_code: int, body: str) -> bool:
    """Return True when an HTTP error is caused by billing/quota, not a code bug."""
    if status_code not in (400, 401, 402, 403, 429):
        return False
    body_lower = body.lower()
    return any(phrase in body_lower for phrase in _BILLING_PHRASES)


@dataclass
class ProviderHealth:
    """Point-in-time health snapshot for a provider."""

    provider_id: str
    healthy: bool
    latency_ms: float = 0.0
    error: Optional[str] = None
    billing_issue: bool = False
    checked_at: float = field(default_factory=time.time)


class BaseProvider(ABC):
    """
    Abstract provider interface.

    Subclasses must implement completion, streaming, and health probing.
    Costs are expressed as USD per 1K tokens to keep routing logic simple.
    """

    def __init__(
        self,
        provider_id: Union[str, Dict[str, Any]],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        resolved_provider_id, resolved_config = self._resolve_init_args(provider_id, config)
        self.provider_id = resolved_provider_id
        self.config = resolved_config
        self.endpoint = str(self.config.get("endpoint", "")).rstrip("/")
        self.api_key_env = self.config.get("api_key_env")
        self.invoke_path = self.config.get("invoke_path", "")
        self._healthy = True
        self._last_error: Optional[str] = None
        self._failure_count = 0
        self._transient_failure_count = 0
        self._circuit_open_until = 0.0
        self._soft_open_probe_taken = False
        self._circuit_state = ProviderCircuitState.CLOSED

        # Shared client configuration
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self, timeout: float = 60.0) -> httpx.AsyncClient:
        """Returns a reusable AsyncClient instance."""
        if self._client is None or self._client.is_closed:
            # Standardizing on a pooled client for the provider instance
            self._client = httpx.AsyncClient(
                timeout=timeout,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
            )
        return self._client

    @staticmethod
    def _resolve_init_args(
        provider_id: Union[str, Dict[str, Any]],
        config: Optional[Dict[str, Any]],
    ) -> tuple[str, Dict[str, Any]]:
        if config is None and isinstance(provider_id, dict):
            resolved_config = dict(provider_id)
            fallback_name = resolved_config.get("name") or "provider"
            normalized = str(fallback_name).strip().lower().replace(" ", "_")
            return normalized, resolved_config

        if isinstance(provider_id, dict):
            resolved_config = dict(config or {})
            return "provider", resolved_config

        return provider_id, dict(config or {})

    @property
    def provider_name(self) -> str:
        return str(self.config.get("name", self.provider_id))

    @property
    def default_model(self) -> str:
        return str(self.config.get("default_model", ""))

    def api_key(self, default_env: str = "") -> str:
        env_name = self.api_key_env or default_env
        return os.getenv(env_name, "").strip() if env_name else ""

    def normalize_messages(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        *,
        prompt: str = "",
        **kwargs: Any,
    ) -> List[Dict[str, str]]:
        if isinstance(messages, list) and messages:
            return messages

        kw_messages = kwargs.get("messages")
        if isinstance(kw_messages, list) and kw_messages:
            return kw_messages

        prompt_value = prompt or str(kwargs.get("prompt", ""))
        if prompt_value:
            return [{"role": "user", "content": prompt_value}]

        return []

    @abstractmethod
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
        """Non-streaming completion."""

    @abstractmethod
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
        """Streaming completion."""

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Probe the provider."""

    async def chat(
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
        """V1 adapter surface: chat invocation."""
        return await self.invoke(
            messages=messages,
            model=model,
            stream=stream,
            max_tokens=max_tokens,
            temperature=temperature,
            prompt=prompt,
            **kwargs,
        )

    def stream_chat(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        prompt: str = "",
        **kwargs: Any,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """V1 adapter surface: streaming chat invocation."""
        return self.stream(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            prompt=prompt,
            **kwargs,
        )

    async def health(self) -> ProviderHealth:
        """V1 adapter surface: provider health probe."""
        return await self.health_check()

    async def warmup(self) -> ProviderResult:
        """Optional startup warmup probe."""
        return await self.invoke(
            messages=[{"role": "user", "content": "ping"}],
            model=self.default_model or None,
            max_tokens=1,
            temperature=0.0,
        )

    def warmup_targets(self) -> list[tuple[str, "BaseProvider"]]:
        """Return providers that should receive warmup traffic."""
        return [(self.provider_id, self)]

    def capabilities(self) -> ProviderCapabilityMatrix:
        """V1 capability contract (embeddings optional by design)."""
        configured = {str(item).strip().lower() for item in self.config.get("capabilities", [])}
        supports_embed = "embeddings" in configured or self.config.get("supports_embeddings", False)
        limits: Dict[str, int] = {}
        for source_key, dest_key in (
            ("max_input_tokens", "max_input_tokens"),
            ("max_output_tokens", "max_output_tokens"),
            ("max_batch_size", "max_batch_size"),
        ):
            value = self.config.get(source_key)
            if isinstance(value, int) and value > 0:
                limits[dest_key] = value

        return {
            "chat": True,
            "stream_chat": True,
            "health": True,
            "capabilities": True,
            "embeddings": bool(supports_embed),
            "limits": limits,
        }

    def is_available(self) -> bool:
        if self._circuit_state == ProviderCircuitState.HARD_OPEN:
            return False
        if self._circuit_state == ProviderCircuitState.SOFT_OPEN:
            return True
        if time.time() < self._circuit_open_until:
            return False
        return self._healthy or self._failure_count < 3

    def should_attempt(self, *, canary: bool = False, critical: bool = True) -> bool:
        """Return whether routing may attempt this provider now."""
        if self._circuit_state == ProviderCircuitState.HARD_OPEN:
            return False
        if self._circuit_state == ProviderCircuitState.SOFT_OPEN:
            return bool(canary and self.soft_open_probe_available())
        return self.is_available()

    def soft_open_probe_available(self) -> bool:
        """Return True when a soft-open provider may receive its next probe."""
        return (
            self._circuit_state == ProviderCircuitState.SOFT_OPEN
            and not self._soft_open_probe_taken
            and time.time() >= self._circuit_open_until
        )

    def claim_soft_open_probe(self) -> bool:
        """Reserve the current soft-open probe slot if one is available."""
        if not self.soft_open_probe_available():
            return False
        self._soft_open_probe_taken = True
        return True

    @property
    def circuit_state(self) -> str:
        return self._circuit_state.value

    def circuit_status(self) -> Dict[str, Any]:
        cooldown_remaining_seconds = 0.0
        if self._circuit_open_until not in (0.0, float("inf")):
            cooldown_remaining_seconds = max(0.0, self._circuit_open_until - time.time())
        return {
            "state": self._circuit_state.value,
            "failure_count": self._failure_count,
            "transient_failure_count": self._transient_failure_count,
            "last_error": self._last_error,
            "open_until": self._circuit_open_until,
            "cooldown_remaining_seconds": round(cooldown_remaining_seconds, 1),
            "probe_available": self.soft_open_probe_available(),
            "probe_taken": self._soft_open_probe_taken,
            "available": self.is_available(),
        }

    def record_failure(
        self,
        error: str,
        backoff_seconds: float = 30.0,
        category: Optional[Union[ProviderErrorCategory, str]] = None,
    ) -> None:
        category_value = self._normalize_error_category(error, category)
        self._failure_count += 1
        self._last_error = error
        if self._circuit_state == ProviderCircuitState.HARD_OPEN:
            self._healthy = False
            return
        if category_value == ProviderErrorCategory.AUTH or (
            category_value in {ProviderErrorCategory.RATE_LIMIT, ProviderErrorCategory.UNKNOWN}
            and is_billing_error(429, error)
        ):
            self._healthy = False
            self._circuit_state = ProviderCircuitState.HARD_OPEN
            self._circuit_open_until = float("inf")
            self._soft_open_probe_taken = False
            return

        if self._circuit_state == ProviderCircuitState.SOFT_OPEN:
            self._healthy = False
            self._circuit_open_until = time.time() + backoff_seconds
            self._soft_open_probe_taken = False
            if category_value in {
                ProviderErrorCategory.TIMEOUT,
                ProviderErrorCategory.SERVER_ERROR,
            }:
                self._transient_failure_count += 1
            elif category_value not in {
                ProviderErrorCategory.AUTH,
                ProviderErrorCategory.RATE_LIMIT,
            }:
                self._transient_failure_count = 0
            return

        if category_value in {ProviderErrorCategory.TIMEOUT, ProviderErrorCategory.SERVER_ERROR}:
            self._transient_failure_count += 1
        else:
            self._transient_failure_count = 0

        if self._transient_failure_count >= 2 or self._failure_count >= 3:
            self._circuit_state = ProviderCircuitState.SOFT_OPEN
            self._healthy = False
            self._circuit_open_until = time.time() + backoff_seconds
            self._soft_open_probe_taken = False

    def record_success(self) -> None:
        self._healthy = True
        self._failure_count = 0
        self._transient_failure_count = 0
        self._last_error = None
        self._circuit_open_until = 0.0
        self._soft_open_probe_taken = False
        self._circuit_state = ProviderCircuitState.CLOSED

    def reset_circuit(self) -> None:
        self.record_success()

    @staticmethod
    def _normalize_error_category(
        error: str,
        category: Optional[Union[ProviderErrorCategory, str]],
    ) -> ProviderErrorCategory:
        if isinstance(category, ProviderErrorCategory):
            return category
        if isinstance(category, str) and category:
            try:
                return ProviderErrorCategory(category.strip().lower().replace("_", "-"))
            except ValueError:
                pass
        return classify_provider_error(error)

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: Optional[str] = None,
    ) -> float:
        resolved_model = model or self.default_model or None
        pricing = resolve_model_pricing(
            self.provider_id,
            resolved_model,
            config=self.config,
        )
        return (
            input_tokens * pricing.input_per1k / 1000 + output_tokens * pricing.output_per1k / 1000
        )

    async def embed(
        self,
        texts: Union[str, List[str]],
        model: str = "",
        **kwargs: Any,
    ) -> Union[List[float], List[List[float]]]:
        raise RuntimeError(f"{self.__class__.__name__} does not support embeddings")

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "BaseProvider":
        return cls(config)
