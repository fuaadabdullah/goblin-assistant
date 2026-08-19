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

from .domain import ProviderHealthSnapshot as ProviderHealth


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
    """Compatibility circuit states shared by providers and dispatcher code."""

    CLOSED = "closed"
    SOFT_OPEN = "soft_open"
    HARD_OPEN = "hard_open"

    @classmethod
    def from_value(cls, value: Any) -> "ProviderCircuitState":
        if isinstance(value, cls):
            return value
        raw = getattr(value, "value", value)
        normalized = str(raw or "").strip().lower().replace("-", "_")
        if normalized in {"", "open"}:
            return cls.HARD_OPEN if normalized == "open" else cls.CLOSED
        if normalized == "half_open":
            return cls.SOFT_OPEN
        try:
            return cls(normalized)
        except ValueError:
            return cls.CLOSED


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


def _normalize_error_category(
    category: Any,
    error: str,
) -> ProviderErrorCategory:
    if isinstance(category, ProviderErrorCategory):
        return category
    raw = getattr(category, "value", category)
    if raw is None:
        return classify_provider_error(error)
    normalized = str(raw).strip().lower().replace("_", "-")
    try:
        return ProviderErrorCategory(normalized)
    except ValueError:
        return classify_provider_error(error)


def _is_hard_open_failure(
    category: ProviderErrorCategory,
    error: str,
) -> bool:
    if category in {ProviderErrorCategory.AUTH, ProviderErrorCategory.RATE_LIMIT}:
        return True
    error_lower = error.lower()
    if any(phrase in error_lower for phrase in _BILLING_PHRASES):
        return True
    if any(
        phrase in error_lower
        for phrase in (
            "access denied",
            "access_denied",
            "model_access_denied",
            "forbidden",
            "unauthorized",
            "invalid api key",
            "invalid_api_key",
        )
    ):
        return True
    return False


class BaseProvider(ABC):
    """
    Abstract provider interface.

    Subclasses must implement completion, streaming, and health probing.
    Costs are expressed as USD per 1K tokens to keep routing logic simple.
    """

    COST_INPUT_PER_1K: float = 0.0
    COST_OUTPUT_PER_1K: float = 0.0
    SOFT_OPEN_FAILURE_THRESHOLD: int = 2
    SOFT_OPEN_BACKOFF_SECONDS: float = 30.0

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
        self._last_failure_time = 0.0
        self._circuit_open_until = 0.0
        self._circuit_state = ProviderCircuitState.CLOSED
        self._probe_taken = False

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

    @property
    def circuit_state(self) -> str:
        return self._circuit_state.value

    @circuit_state.setter
    def circuit_state(self, value: Any) -> None:
        state = ProviderCircuitState.from_value(value)
        self._circuit_state = state
        if state == ProviderCircuitState.CLOSED:
            self._circuit_open_until = 0.0
            self._probe_taken = False
            self._healthy = True
        elif state == ProviderCircuitState.SOFT_OPEN:
            if self._circuit_open_until <= 0.0 or self._circuit_open_until == float("inf"):
                self._circuit_open_until = time.time() + self.SOFT_OPEN_BACKOFF_SECONDS
            self._probe_taken = False
            self._healthy = False
        else:
            self._circuit_open_until = float("inf")
            self._probe_taken = False
            self._healthy = False

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
    ) -> "ProviderResult":
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
        return self.stream(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            prompt=prompt,
            **kwargs,
        )

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
        """Streaming completion."""

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Probe the provider."""

    async def warmup(self) -> ProviderResult:
        """Run a minimal live completion probe for access validation."""
        return await self.invoke(
            messages=[{"role": "user", "content": "ping"}],
            model=self.default_model or None,
            max_tokens=1,
            temperature=0.0,
        )

    async def invoke_typed(
        self,
        request: "ProviderExecutionRequest",  # noqa: F821
    ) -> "ProviderExecutionResult":  # noqa: F821
        from .domain import from_provider_result  # noqa: PLC0415

        result = await self.invoke(
            messages=request.messages,
            model=request.model,
            stream=request.stream,
            max_tokens=request.max_tokens or 4096,
            temperature=request.temperature or 0.7,
            prompt=request.prompt or "",
            **request.extra,
        )
        return from_provider_result(
            result,
            provider_id=request.provider_id,
            model=request.model,
        )

    async def health(
        self,
    ) -> "ProviderHealth":
        return await self.health_check()

    def capabilities(self) -> Dict[str, Any]:
        raw_caps = self.config.get("capabilities", [])
        configured_caps = (
            {str(item).strip().lower() for item in raw_caps if str(item).strip()}
            if isinstance(raw_caps, list)
            else set()
        )
        limits: Dict[str, int] = {}
        for key in ("max_input_tokens", "max_output_tokens", "max_batch_size"):
            value = self.config.get(key)
            if isinstance(value, int) and value > 0:
                limits[key] = value
        return {
            "chat": True,
            "stream_chat": True,
            "health": True,
            "capabilities": True,
            "embeddings": "embeddings" in configured_caps
            or type(self).embed is not BaseProvider.embed,
            "reranking": "reranking" in configured_caps or hasattr(self, "rerank"),
            "limits": limits,
        }

    def capabilities_typed(self):
        from .domain import capabilities_from_matrix  # noqa: PLC0415

        return capabilities_from_matrix(self.capabilities())

    def is_available(self) -> bool:
        return self._circuit_state != ProviderCircuitState.HARD_OPEN

    def should_attempt(self, *, canary: bool = False) -> bool:
        if self._circuit_state == ProviderCircuitState.HARD_OPEN:
            return False
        if self._circuit_state == ProviderCircuitState.SOFT_OPEN:
            return bool(canary and self.soft_open_probe_available())
        return True

    def soft_open_probe_available(self) -> bool:
        if self._circuit_state != ProviderCircuitState.SOFT_OPEN:
            return False
        if self._probe_taken:
            return False
        return time.time() >= self._circuit_open_until

    def claim_soft_open_probe(self) -> bool:
        if not self.soft_open_probe_available():
            return False
        self._probe_taken = True
        return True

    def circuit_status(self) -> Dict[str, Any]:
        now = time.time()
        state = self.circuit_state
        open_until = (
            self._circuit_open_until
            if self._circuit_state == ProviderCircuitState.SOFT_OPEN
            else 0.0
        )
        cooldown_remaining = max(0.0, open_until - now) if open_until else 0.0
        probe_available = self.soft_open_probe_available()
        return {
            "state": state,
            "circuit_state": state,
            "available": self.is_available(),
            "healthy": self.is_available(),
            "failure_count": self._failure_count,
            "failure_threshold": self.SOFT_OPEN_FAILURE_THRESHOLD,
            "transient_failure_count": self._transient_failure_count,
            "last_error": self._last_error,
            "last_failure_time": self._last_failure_time,
            "open_until": open_until,
            "cooldown_remaining_seconds": round(cooldown_remaining, 1),
            "time_until_recovery": round(cooldown_remaining, 1),
            "probe_available": probe_available,
            "probe_taken": self._probe_taken,
        }

    def reset_circuit(self) -> None:
        self.record_success()

    def record_failure(
        self,
        error: str,
        backoff_seconds: float = 30.0,
        *,
        category: Optional[Union[str, ProviderErrorCategory]] = None,
    ) -> None:
        now = time.time()
        self._failure_count += 1
        self._last_error = error
        self._last_failure_time = now

        normalized_category = _normalize_error_category(category, error)
        if _is_hard_open_failure(normalized_category, error):
            self._circuit_state = ProviderCircuitState.HARD_OPEN
            self._circuit_open_until = float("inf")
            self._transient_failure_count = 0
            self._probe_taken = False
            self._healthy = False
            return

        if self._circuit_state == ProviderCircuitState.HARD_OPEN:
            self._healthy = False
            return

        self._healthy = False
        if normalized_category == ProviderErrorCategory.MODEL_ERROR:
            return

        self._transient_failure_count += 1
        if (
            self._circuit_state == ProviderCircuitState.SOFT_OPEN
            or self._transient_failure_count >= self.SOFT_OPEN_FAILURE_THRESHOLD
        ):
            self._circuit_state = ProviderCircuitState.SOFT_OPEN
            self._circuit_open_until = now + max(
                0.0, backoff_seconds or self.SOFT_OPEN_BACKOFF_SECONDS
            )
            self._probe_taken = False
        else:
            self._circuit_state = ProviderCircuitState.CLOSED
            self._circuit_open_until = 0.0
            self._probe_taken = False

    def record_success(self) -> None:
        self._healthy = True
        self._failure_count = 0
        self._transient_failure_count = 0
        self._last_error = None
        self._last_failure_time = 0.0
        self._circuit_open_until = 0.0
        self._circuit_state = ProviderCircuitState.CLOSED
        self._probe_taken = False

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        *,
        model: Optional[str] = None,
    ) -> float:
        try:
            from .pricing import estimate_cost as resolve_cost  # noqa: PLC0415

            configured_cost = resolve_cost(
                self.provider_id,
                input_tokens,
                output_tokens,
                model=model,
                config=self.config,
            )
        except Exception:
            configured_cost = 0.0

        if configured_cost > 0:
            return configured_cost

        return (
            input_tokens * self.COST_INPUT_PER_1K / 1000
            + output_tokens * self.COST_OUTPUT_PER_1K / 1000
        )

    async def embed(
        self,
        texts: Union[str, List[str]],
        model: str = "",
        **kwargs: Any,
    ) -> Union[List[float], List[List[float]]]:
        raise NotImplementedError(f"{self.__class__.__name__} does not support embeddings")

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "BaseProvider":
        return cls(config)
