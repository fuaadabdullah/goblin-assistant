"""
Base provider abstraction for Goblin Assistant.

All provider implementations share the same response model, circuit breaker,
and compatibility helpers so callers can keep using the legacy dispatcher
contract while the internals use a stricter typed core.
"""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional, Union


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
            "result": {
                "text": self.text,
                "raw": self.raw,
                "usage": self.usage,
                "cost_usd": self.cost_usd,
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
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

    def get(self, key: str, default: Any = None) -> Any:
        return self._compat_dict().get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._compat_dict()[key]

    def __contains__(self, key: object) -> bool:
        return key in self._compat_dict()


@dataclass
class ProviderHealth:
    """Point-in-time health snapshot for a provider."""

    provider_id: str
    healthy: bool
    latency_ms: float = 0.0
    error: Optional[str] = None
    checked_at: float = field(default_factory=time.time)


class BaseProvider(ABC):
    """
    Abstract provider interface.

    Subclasses must implement completion, streaming, and health probing.
    Costs are expressed as USD per 1K tokens to keep routing logic simple.
    """

    COST_INPUT_PER_1K: float = 0.0
    COST_OUTPUT_PER_1K: float = 0.0

    def __init__(
        self,
        provider_id: Union[str, Dict[str, Any]],
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        resolved_provider_id, resolved_config = self._resolve_init_args(
            provider_id, config
        )
        self.provider_id = resolved_provider_id
        self.config = resolved_config
        self.endpoint = str(self.config.get("endpoint", "")).rstrip("/")
        self.api_key_env = self.config.get("api_key_env")
        self.invoke_path = self.config.get("invoke_path", "")
        self._healthy = True
        self._last_error: Optional[str] = None
        self._failure_count = 0
        self._circuit_open_until = 0.0

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

    def is_available(self) -> bool:
        if time.time() < self._circuit_open_until:
            return False
        return self._healthy or self._failure_count < 3

    def record_failure(self, error: str, backoff_seconds: float = 30.0) -> None:
        self._failure_count += 1
        self._last_error = error
        if self._failure_count >= 3:
            self._healthy = False
            self._circuit_open_until = time.time() + backoff_seconds

    def record_success(self) -> None:
        self._healthy = True
        self._failure_count = 0
        self._last_error = None
        self._circuit_open_until = 0.0

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
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
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support embeddings"
        )

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "BaseProvider":
        return cls(config)
