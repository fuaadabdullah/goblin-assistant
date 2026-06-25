from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterable, List

import structlog

_JSON_SECRET_RE = re.compile(
    r'("(?:api[_-]?key|access[_-]?token|authorization|secret|password)"\s*:\s*")([^"]+)(")',
    re.IGNORECASE,
)
_KV_SECRET_RE = re.compile(
    r"((?:api[_-]?key|access[_-]?token|authorization|secret|password)\s*[:=]\s*)([^,\s;]+)",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"(bearer\s+)([A-Za-z0-9._\-]+)", re.IGNORECASE)
_OPENAI_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")

EXTRA_SECRET_ENV_NAMES = {
    "AZURE_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "VERTEX_AI_SERVICE_ACCOUNT_JSON",
    "GCP_SERVICE_ACCOUNT_KEY",
}

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(api[_-]?key|access[_-]?token|authorization|secret|password|credential|bearer|token)",
    re.IGNORECASE,
)
_SAFE_EVENT_KEYS = {
    "event",
    "provider",
    "provider_id",
    "model",
    "engine",
    "status_code",
    "latency_ms",
    "error_category",
    "circuit_state",
    "configured",
    "configured_count",
    "unconfigured",
    "unconfigured_count",
    "total",
    "request_id",
    "cost_weight",
    "candidates",
    "rank_order",
    "score_breakdown",
    "path",
    "hint",
    "reason",
    "billing_issue",
    "impact",
    "action",
    "state",
}


def known_secrets(configs: Dict[str, Dict[str, Any]]) -> List[str]:
    secrets: set[str] = set()
    for raw_config in configs.values():
        if not isinstance(raw_config, dict):
            continue
        api_key_env = str(raw_config.get("api_key_env", "") or "").strip()
        if not api_key_env:
            continue
        secret = os.getenv(api_key_env, "").strip()
        if secret:
            secrets.add(secret)

    for env_name in EXTRA_SECRET_ENV_NAMES:
        secret = os.getenv(env_name, "").strip()
        if secret:
            secrets.add(secret)
    return list(secrets)


def sanitize_error_message(message: str, secrets: Iterable[str]) -> str:
    sanitized = str(message)
    if not sanitized:
        return sanitized

    for secret in sorted({s for s in secrets if len(s) >= 8}, key=len, reverse=True):
        sanitized = sanitized.replace(secret, "[REDACTED]")

    sanitized = _JSON_SECRET_RE.sub(r"\1[REDACTED]\3", sanitized)
    sanitized = _KV_SECRET_RE.sub(r"\1[REDACTED]", sanitized)
    sanitized = _BEARER_RE.sub(r"\1[REDACTED]", sanitized)
    sanitized = _OPENAI_KEY_RE.sub("[REDACTED]", sanitized)
    return sanitized


def sanitize_log_value(value: Any, secrets: Iterable[str]) -> Any:
    if isinstance(value, str):
        return sanitize_error_message(value, secrets)
    if isinstance(value, dict):
        sanitized: Dict[str, Any] = {}
        for key, item in value.items():
            key_str = str(key)
            if _SENSITIVE_KEY_PATTERN.search(key_str):
                sanitized[key_str] = "[REDACTED]"
                continue
            sanitized[key_str] = sanitize_log_value(item, secrets)
        return sanitized
    if isinstance(value, (list, tuple, set)):
        return [sanitize_log_value(item, secrets) for item in value]
    return value


def provider_secrets_processor(
    secrets_supplier,
):
    def processor(_logger: Any, _method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        secrets = list(secrets_supplier())
        sanitized: Dict[str, Any] = {}
        for key, value in event_dict.items():
            if key.startswith("_"):
                continue
            if (
                key != "event"
                and key not in _SAFE_EVENT_KEYS
                and _SENSITIVE_KEY_PATTERN.search(key)
            ):
                sanitized[key] = "[REDACTED]"
                continue
            sanitized[key] = sanitize_log_value(value, secrets)
        return sanitized

    return processor


class ProviderLoggerProxy:
    def __init__(
        self, name: str, secrets_supplier, *, context: Dict[str, Any] | None = None
    ) -> None:
        self._name = name
        self._secrets_supplier = secrets_supplier
        self._logger = structlog.get_logger(name)
        self._processor = provider_secrets_processor(secrets_supplier)
        self._context = dict(context or {})

    def bind(self, **kwargs: Any) -> "ProviderLoggerProxy":
        next_context = dict(self._context)
        next_context.update(kwargs)
        return ProviderLoggerProxy(self._name, self._secrets_supplier, context=next_context)

    def _emit(self, level: str, event: str, **kwargs: Any) -> Any:
        event_dict = {"event": event, **self._context, **kwargs}
        sanitized = self._processor(self._logger, level, event_dict)
        payload = dict(sanitized)
        payload.pop("event", None)
        return getattr(self._logger, level)(event, **payload)

    def debug(self, event: str, **kwargs: Any) -> Any:
        return self._emit("debug", event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> Any:
        return self._emit("info", event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> Any:
        return self._emit("warning", event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> Any:
        return self._emit("error", event, **kwargs)

    def critical(self, event: str, **kwargs: Any) -> Any:
        return self._emit("critical", event, **kwargs)


def get_provider_logger(name: str, secrets_supplier):
    return ProviderLoggerProxy(name, secrets_supplier)
