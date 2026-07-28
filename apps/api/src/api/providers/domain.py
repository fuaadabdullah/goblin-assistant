"""Shared provider vocabulary: capability, metadata, health, and execution types.

This module is the boundary contract between `providers/` and `routing/` —
neither package should need to reach past these types into the other's
internals. It has no runtime dependency on `base.py` (base.py imports from
here instead — see the ProviderHealth/ProviderErrorCategory re-exports
there), no dependency on `provider_registry.py`/`model_registry.py` (the
registry/factory layer depends on this module, never the reverse), and no
dependency on `routing/`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Optional

from .contracts import ProviderCapabilityLimits


class ProviderErrorCategory(str, Enum):
    """Structured error categories for provider failures.

    Owned here (not base.py) so this module has zero runtime dependency on
    base.py — base.py re-exports this name for backward compatibility with
    every existing `from .base import ProviderErrorCategory` import site.
    """

    AUTH = "auth"  # 401/403, invalid API key
    RATE_LIMIT = "rate-limit"  # 429, quota exceeded
    TIMEOUT = "timeout"  # Connection/read timeout
    MODEL_ERROR = "model-error"  # Invalid model, context too long
    SERVER_ERROR = "server-error"  # 5xx from provider
    CONNECTION = "connection"  # DNS, network, connection refused
    UNKNOWN = "unknown"


class ProviderCapability(str, Enum):
    """Closed set of capabilities a provider can advertise.

    Values match the raw strings already used in providers.toml and the
    ProviderCapabilityMatrix boolean keys, so parsing existing config is a
    direct lookup rather than a translation table.
    """

    CHAT = "chat"
    STREAM_CHAT = "stream_chat"
    EMBEDDINGS = "embeddings"
    HEALTH = "health"
    RERANKING = "reranking"


def capabilities_from_config_list(raw: list[str]) -> frozenset[ProviderCapability]:
    """Parse a raw providers.toml `capabilities` list, ignoring unknown strings."""
    result = set()
    for item in raw:
        normalized = str(item).strip().lower()
        try:
            result.add(ProviderCapability(normalized))
        except ValueError:
            continue
    return frozenset(result)


def capabilities_from_matrix(matrix: Mapping[str, Any]) -> frozenset[ProviderCapability]:
    """Bridge the computed ProviderCapabilityMatrix (BaseProvider.capabilities()) into the enum set.

    Typed as Mapping[str, Any] rather than ProviderCapabilityMatrix: the
    TypedDict declares chat/stream_chat/health/capabilities/embeddings/limits,
    but GoogleCloudProvider.capabilities() (google_cloud_provider.py) mutates
    the dict returned by super().capabilities() to add an undeclared
    top-level "reranking": True key, which this function must also read.
    """
    result = set()
    if matrix.get("chat"):
        result.add(ProviderCapability.CHAT)
    if matrix.get("stream_chat"):
        result.add(ProviderCapability.STREAM_CHAT)
    if matrix.get("health"):
        result.add(ProviderCapability.HEALTH)
    if matrix.get("embeddings"):
        result.add(ProviderCapability.EMBEDDINGS)
    if matrix.get("reranking"):
        result.add(ProviderCapability.RERANKING)
    return frozenset(result)


@dataclass(frozen=True)
class ProviderMetadata:
    """Typed replacement for the raw provider config dict passed around today."""

    provider_id: str
    display_name: str
    capabilities: frozenset[ProviderCapability]
    default_model: Optional[str]
    models: tuple[str, ...]
    limits: ProviderCapabilityLimits
    configured: bool
    extra: Mapping[str, Any] = field(default_factory=dict)


class ProviderHealthStatus(str, Enum):
    """Local, provider-owned health status enum.

    Deliberately not an import of services.provider_health.HealthStatus —
    that would create a providers -> services (ops/monitor) dependency in
    the wrong direction. Values mirror HealthStatus so a future merge is a
    rename, not a redesign.
    """

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    BILLING_ISSUE = "billing_issue"


@dataclass(frozen=True)
class ProviderHealthSnapshot:
    """Point-in-time health snapshot for a provider.

    Constructor-compatible with providers.base.ProviderHealth so
    `ProviderHealth = ProviderHealthSnapshot` (see base.py) is a lossless
    alias for every provider's health_check() implementation: all 17
    concrete providers construct ProviderHealth with `provider_id` and
    `healthy` positional and everything else by keyword, never passing
    `status` — so `status` must have a default. When omitted, it's derived
    from `healthy`/`billing_issue`.
    """

    provider_id: str
    healthy: bool
    status: Optional[ProviderHealthStatus] = None
    latency_ms: float = 0.0
    error: Optional[str] = None
    billing_issue: bool = False
    checked_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if self.status is not None:
            return
        if self.billing_issue:
            derived = ProviderHealthStatus.BILLING_ISSUE
        elif self.healthy:
            derived = ProviderHealthStatus.HEALTHY
        else:
            derived = ProviderHealthStatus.UNHEALTHY
        object.__setattr__(self, "status", derived)


@dataclass(frozen=True)
class ProviderExecutionRequest:
    """Typed replacement for the bare `payload: Dict[str, Any]` threaded through
    routing/selection.py -> dispatcher.invoke_provider -> BaseProvider.invoke."""

    provider_id: str
    model: str
    messages: list[Dict[str, Any]]
    stream: bool = False
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    prompt: Optional[str] = None
    timeout_ms: int = 30_000
    routing_mode: Optional[str] = None
    dry_run: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


_EXECUTION_REQUEST_KNOWN_KEYS = frozenset(
    {
        "messages",
        "model",
        "stream",
        "prompt",
        "max_tokens",
        "temperature",
        "timeout_ms",
        "routing_mode",
        "dry_run",
    }
)


def to_payload_dict(req: ProviderExecutionRequest) -> Dict[str, Any]:
    """Convert to the plain dict shape dispatcher.invoke_provider/execution.py expect.

    Deliberately omits "stream": dispatcher_pkg/test_mode.py's invoke_with_test_mode
    calls provider.invoke(messages, model, stream=False, **kwargs) — if "stream" is
    also present in kwargs (i.e. leaked into the payload dict), that's a duplicate
    keyword argument and raises at call time. `stream` must flow as the separate
    `stream=` argument to invoke_provider/dispatch, never as a payload dict key.
    """
    payload: Dict[str, Any] = {
        "messages": req.messages,
        "model": req.model,
        "timeout_ms": req.timeout_ms,
    }
    if req.prompt is not None:
        payload["prompt"] = req.prompt
    if req.max_tokens is not None:
        payload["max_tokens"] = req.max_tokens
    if req.temperature is not None:
        payload["temperature"] = req.temperature
    if req.routing_mode is not None:
        payload["routing_mode"] = req.routing_mode
    if req.dry_run:
        payload["dry_run"] = req.dry_run
    payload.update(req.extra)
    return payload


def from_payload_dict(
    d: Mapping[str, Any],
    *,
    provider_id: str,
    model: str,
    **overrides: Any,
) -> ProviderExecutionRequest:
    """Build a typed request from a plain payload dict (the reverse of to_payload_dict)."""
    extra = {k: v for k, v in d.items() if k not in _EXECUTION_REQUEST_KNOWN_KEYS}
    kwargs: Dict[str, Any] = {
        "provider_id": provider_id,
        "model": model,
        "messages": list(d.get("messages") or []),
        "stream": bool(d.get("stream", False)),
        "max_tokens": d.get("max_tokens"),
        "temperature": d.get("temperature"),
        "prompt": d.get("prompt"),
        "timeout_ms": int(d.get("timeout_ms", 30_000) or 30_000),
        "routing_mode": d.get("routing_mode"),
        "dry_run": bool(d.get("dry_run", False)),
        "extra": extra,
    }
    kwargs.update(overrides)
    return ProviderExecutionRequest(**kwargs)


@dataclass(frozen=True)
class ProviderExecutionResult:
    """Typed replacement for the ProviderResult.to_dict() flattening done in
    dispatcher_pkg/execution.py today."""

    ok: bool
    provider_id: str
    model: str
    text: Optional[str] = None
    raw: Any = None
    usage: Mapping[str, Any] = field(default_factory=dict)
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    error: Optional[str] = None
    error_category: Optional[ProviderErrorCategory] = None


def from_provider_result(pr: Any, *, provider_id: str, model: str) -> ProviderExecutionResult:
    """Build a ProviderExecutionResult from a providers.base.ProviderResult.

    Typed as `Any` (duck-typed) rather than importing ProviderResult: this
    module has zero dependency on base.py by design (base.py depends on
    this module, not the reverse). Only attribute access is used below —
    `pr` just needs `.ok`, `.text`, `.raw`, `.usage`, `.cost_usd`,
    `.latency_ms`, `.error`, `.error_category`.
    """
    error_category: Optional[ProviderErrorCategory] = None
    if pr.error_category:
        try:
            error_category = ProviderErrorCategory(pr.error_category)
        except ValueError:
            error_category = None
    return ProviderExecutionResult(
        ok=pr.ok,
        provider_id=provider_id,
        model=model,
        text=pr.text or None,
        raw=pr.raw,
        usage=dict(pr.usage or {}),
        cost_usd=float(pr.cost_usd or 0.0),
        latency_ms=pr.latency_ms,
        error=pr.error,
        error_category=error_category,
    )


def from_execution_dict(
    d: Mapping[str, Any], *, provider_id: str, model: str
) -> ProviderExecutionResult:
    """Build a ProviderExecutionResult from the plain dict dispatcher.invoke_provider
    returns today (dispatcher_pkg/execution.py flattens ProviderResult.to_dict()
    into this shape, with a nested "result" sub-dict on the success path and a
    flat {"ok": False, "error": ..., "latency_ms": ...} shape on early exits)."""
    result_section = d.get("result")
    if not isinstance(result_section, Mapping):
        result_section = {}

    error_category_raw = d.get("error_category")
    error_category: Optional[ProviderErrorCategory] = None
    if error_category_raw:
        try:
            error_category = ProviderErrorCategory(error_category_raw)
        except ValueError:
            error_category = None

    return ProviderExecutionResult(
        ok=bool(d.get("ok", False)),
        provider_id=str(d.get("provider") or provider_id),
        model=str(d.get("model") or model),
        text=result_section.get("text", d.get("text")),
        raw=result_section.get("raw", d.get("raw")),
        usage=dict(result_section.get("usage") or d.get("usage") or {}),
        cost_usd=float(result_section.get("cost_usd") or d.get("cost_usd") or 0.0),
        latency_ms=float(d.get("latency_ms", 0.0) or 0.0),
        error=d.get("error"),
        error_category=error_category,
    )
