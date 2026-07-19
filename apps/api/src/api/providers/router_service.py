"""In-process LiteLLM router for logical model groups.

Phase 1 keeps LiteLLM embedded in the FastAPI process so logical model names
can route across multiple concrete deployments without a separate proxy.
"""

from __future__ import annotations

import base64
import inspect
import json
import os
import re
import time
from dataclasses import dataclass, replace
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional
from urllib.parse import urlparse

import structlog

from ..observability import record_router_cost_guard_event
from ..storage.usage_events import usage_event_store
from .provider_config_runtime import (
    ProviderToml,
    RouterBackend,
    RouterModelGroup,
    load_provider_config,
)

logger = structlog.get_logger(__name__)

ROUTER_PROVIDER_ID = "litellm_router"
ROUTER_LOGICAL_MODELS = ("router-cheap", "router-code", "router-reason")
TASK_ROUTER_MODEL_MAP = {
    "code": "router-code",
    "chat": "router-cheap",
    "long-doc": "router-reason",
}

_AUTO_MODEL_NAMES = {"", "auto", "cheapest", "local"}
_ROUTER_REASON_KILL_SWITCH_ENV = "ROUTER_REASON_DAILY_SPEND_CAP_USD"
_ROUTER_REASON_FALLBACK_MODEL = "router-code"

_CODE_BLOCK_RE = re.compile(r"```|`[^`]+`|^\s*(def|class|import|from)\s+", re.MULTILINE)
_CODE_HINT_RE = re.compile(
    r"(typeerror|syntaxerror|traceback|stack trace|stacktrace|npm |pip |pytest|"
    r"python\b|typescript\b|javascript\b|sql\b|import\s+\w+|const\s+\w+|let\s+\w+|"
    r"function\s+\w+|class\s+\w+|def\s+\w+|=>|;\s*$)"
)
_LONG_DOC_RE = re.compile(r"(^#{1,6}\s|\n\s*\n|\bsummary\b|\bsummarize\b|\bexplain\b)")


@dataclass(frozen=True)
class TaskRouteDecision:
    task_class: str
    logical_model: str
    source: str
    confidence: float
    reason: str
    classifier_model: Optional[str] = None
    classifier_backend_litellm_model: Optional[str] = None
    classifier_prompt_tokens: int = 0
    classifier_completion_tokens: int = 0
    classifier_cost_usd: float = 0.0
    signal: Optional[str] = None
    signal_count: int = 0

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "task_class": self.task_class,
            "logical_model": self.logical_model,
            "classifier_source": self.source,
            "classifier_confidence": round(self.confidence, 4),
            "classifier_reason": self.reason,
            "classifier_model": self.classifier_model,
            "classifier_backend_litellm_model": self.classifier_backend_litellm_model,
            "classifier_prompt_tokens": self.classifier_prompt_tokens,
            "classifier_completion_tokens": self.classifier_completion_tokens,
            "classifier_cost_usd": round(self.classifier_cost_usd, 8),
            "signal": self.signal,
            "signal_count": self.signal_count,
        }


_COMMON_REQUEST_KEYS = {
    "messages",
    "prompt",
    "temperature",
    "top_p",
    "n",
    "stop",
    "max_tokens",
    "max_completion_tokens",
    "stream_options",
    "tools",
    "tool_choice",
    "response_format",
    "seed",
    "metadata",
}


def _load_router_class() -> Optional[type[Any]]:
    try:
        from litellm import Router as LiteLLMRouter

        return LiteLLMRouter
    except Exception:
        return None


def _resolve_env_value(name: Optional[str]) -> str:
    if not name:
        return ""
    return os.getenv(name, "").strip()


def _resolve_vertex_location(backend: RouterBackend) -> str:
    for env_name in (
        backend.vertex_location_env,
        "VERTEX_AI_LOCATION",
        "VERTEXAI_LOCATION",
        "GCP_REGION",
    ):
        value = _resolve_env_value(env_name)
        if value:
            return value
    return ""


def _normalize_vertex_credentials(raw_value: str) -> str:
    if not raw_value:
        return ""
    try:
        if Path(raw_value).exists():
            return raw_value
    except OSError:
        # Inline JSON/base64 credential content can exceed the filesystem's
        # NAME_MAX for a single path component (e.g. Linux's 255-byte
        # limit) — Path.exists() raises instead of returning False in that
        # case. Treat that as "not a path" and keep evaluating raw_value as
        # inline credential content below.
        pass
    if raw_value.startswith("{"):
        try:
            parsed = json.loads(raw_value)
        except Exception:
            return ""
        if isinstance(parsed, dict) and parsed.get("type") in {
            "service_account",
            "authorized_user",
            "external_account",
        }:
            return raw_value
        return ""
    try:
        decoded = base64.b64decode(raw_value).decode("utf-8")
    except Exception:
        return ""
    try:
        parsed = json.loads(decoded)
    except Exception:
        return ""
    if isinstance(parsed, dict) and parsed.get("type") in {
        "service_account",
        "authorized_user",
        "external_account",
    }:
        return decoded
    return ""


def _resolve_vertex_credentials(backend: RouterBackend) -> str:
    for env_name in (
        backend.vertex_credentials_env,
        "GOOGLE_APPLICATION_CREDENTIALS",
        "VERTEX_AI_SERVICE_ACCOUNT_JSON",
        "GCP_SERVICE_ACCOUNT_KEY",
    ):
        resolved = _resolve_env_value(env_name)
        if not resolved:
            continue
        normalized = _normalize_vertex_credentials(resolved)
        if normalized:
            return normalized
    return ""


def _router_config(provider_toml: Optional[ProviderToml] = None) -> Dict[str, RouterModelGroup]:
    config = provider_toml or load_provider_config(use_cache=True)
    return dict(config.router_models)


def _router_group(
    model_name: str, provider_toml: Optional[ProviderToml] = None
) -> Optional[RouterModelGroup]:
    return _router_config(provider_toml).get(model_name)


def get_router_model_names(provider_toml: Optional[ProviderToml] = None) -> List[str]:
    return sorted(_router_config(provider_toml))


def get_router_model_groups(
    provider_toml: Optional[ProviderToml] = None,
) -> Dict[str, RouterModelGroup]:
    return _router_config(provider_toml)


def get_router_model_group(
    model_name: str, provider_toml: Optional[ProviderToml] = None
) -> Optional[RouterModelGroup]:
    return _router_group(model_name, provider_toml)


def _extract_request_text(payload: Dict[str, Any]) -> str:
    parts: List[str] = []
    prompt = payload.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        parts.append(prompt.strip())
    messages = payload.get("messages")
    if isinstance(messages, list):
        for message in messages:
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                parts.append(content.strip())
    return "\n".join(parts).strip()


def _build_heuristic_decision(
    text: str,
    *,
    requested_model: Optional[str] = None,
) -> TaskRouteDecision:
    normalized = text.lower().strip()
    char_count = len(text)
    word_count = len(text.split())
    code_signals = 0
    long_doc_signals = 0

    if _CODE_BLOCK_RE.search(text):
        code_signals += 2
    if _CODE_HINT_RE.search(normalized):
        code_signals += 1
    if any(
        marker in normalized
        for marker in (
            "write a function",
            "create a function",
            "implement a function",
            "write code",
            "code review",
            "fix",
            "debug",
            "refactor",
            "implement",
        )
    ):
        code_signals += 1
    if any(
        marker in normalized
        for marker in ("traceback", "stack trace", "exception", "compile error", "syntax error")
    ):
        code_signals += 1

    if char_count >= 4000 or word_count >= 650:
        long_doc_signals += 2
    if char_count >= 1800 or word_count >= 260:
        long_doc_signals += 1
    if _LONG_DOC_RE.search(text):
        long_doc_signals += 1

    if code_signals >= 2 and code_signals >= long_doc_signals:
        task_class = "code"
        confidence = min(0.98, 0.72 + 0.08 * code_signals)
        reason = "heuristic code signals matched"
        signal = "code"
        signal_count = code_signals
    elif long_doc_signals >= 2 and long_doc_signals > code_signals:
        task_class = "long-doc"
        confidence = min(0.96, 0.7 + 0.07 * long_doc_signals)
        reason = "heuristic long-document signals matched"
        signal = "long-doc"
        signal_count = long_doc_signals
    else:
        task_class = "chat"
        confidence = max(0.45, 0.75 - 0.08 * max(code_signals, long_doc_signals))
        if char_count > 0 and char_count < 200:
            reason = "short conversational request"
        else:
            reason = "no strong code or long-document signals"
        signal = "chat"
        signal_count = 0

    return TaskRouteDecision(
        task_class=task_class,
        logical_model=TASK_ROUTER_MODEL_MAP[task_class],
        source="heuristic",
        confidence=round(confidence, 4),
        reason=reason,
        signal=signal,
        signal_count=signal_count,
    )


def _parse_json_object(text: str) -> Dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start >= 0 and end > start:
        candidate = candidate[start : end + 1]
    try:
        parsed = json.loads(candidate)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _decision_from_classification_response(
    response: Dict[str, Any],
    *,
    fallback: TaskRouteDecision,
) -> TaskRouteDecision:
    if not response.get("ok"):
        return fallback
    text = ""
    result = response.get("result")
    if isinstance(result, dict):
        text = str(result.get("text") or "")
    if not text:
        return fallback
    payload = _parse_json_object(text)
    task_class = str(payload.get("class") or payload.get("task_class") or "").strip().lower()
    if task_class not in TASK_ROUTER_MODEL_MAP:
        return fallback
    raw_confidence = payload.get("confidence", fallback.confidence)
    try:
        confidence = float(raw_confidence)
    except Exception:
        confidence = fallback.confidence
    reason = str(payload.get("reason") or payload.get("explanation") or fallback.reason)
    usage = result.get("usage") if isinstance(result, dict) else {}
    prompt_tokens = 0
    completion_tokens = 0
    if isinstance(usage, dict):
        prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)

    routing = response.get("routing") if isinstance(response.get("routing"), dict) else {}
    classifier_model = None
    classifier_backend_litellm_model = None
    classifier_cost_usd = 0.0
    if isinstance(routing, dict):
        classifier_backend_litellm_model = routing.get("backend_litellm_model")
        classifier_model = classifier_backend_litellm_model or routing.get("logical_model")
        backend_provider_id = routing.get("backend_provider_id")
        if backend_provider_id:
            try:
                backend_model = str(classifier_backend_litellm_model or "").split("/", 1)[-1]
                from ..providers.pricing import estimate_cost  # noqa: PLC0415

                classifier_cost_usd = estimate_cost(
                    str(backend_provider_id),
                    prompt_tokens,
                    completion_tokens,
                    model=backend_model or None,
                )
            except Exception:
                classifier_cost_usd = 0.0

    return TaskRouteDecision(
        task_class=task_class,
        logical_model=TASK_ROUTER_MODEL_MAP[task_class],
        source="llm",
        confidence=max(0.0, min(1.0, confidence)),
        reason=reason,
        classifier_model=str(classifier_model or fallback.classifier_model or ""),
        classifier_backend_litellm_model=str(
            classifier_backend_litellm_model or fallback.classifier_backend_litellm_model or ""
        ),
        classifier_prompt_tokens=prompt_tokens,
        classifier_completion_tokens=completion_tokens,
        classifier_cost_usd=classifier_cost_usd,
        signal=payload.get("signal") if isinstance(payload.get("signal"), str) else fallback.signal,
        signal_count=int(payload.get("signal_count") or fallback.signal_count or 0),
    )


async def resolve_task_route(
    payload: Dict[str, Any],
    *,
    requested_model: Optional[str] = None,
    timeout_ms: int = 30_000,
    provider_toml: Optional[ProviderToml] = None,
) -> TaskRouteDecision:
    text = _extract_request_text(payload)
    heuristic = _build_heuristic_decision(text, requested_model=requested_model)

    if heuristic.confidence >= 0.8 or not text.strip():
        return heuristic

    classifier_prompt = (
        "Classify the request into exactly one of: code, chat, long-doc.\n"
        "Return only JSON with keys: class, confidence, reason.\n"
        "Use long-doc for long article/document prompts, code for implementation/debugging,"
        " and chat for ordinary conversation or short Q&A.\n\n"
        f"Request:\n{text}"
    )
    classifier_payload = {
        "messages": [
            {
                "role": "system",
                "content": "You are a routing classifier. Output only strict JSON.",
            },
            {"role": "user", "content": classifier_prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 80,
    }
    response = await route_logical_model(
        "router-cheap",
        classifier_payload,
        timeout_ms=min(timeout_ms, 6000),
        stream=False,
        provider_toml=provider_toml,
        persist=False,
    )
    if not response:
        return heuristic
    return _decision_from_classification_response(response, fallback=heuristic)


def _backend_is_available(backend: RouterBackend) -> bool:
    if not backend.enabled:
        return False
    if backend.api_key_env and not _resolve_env_value(backend.api_key_env):
        return False
    if backend.endpoint_env and not _resolve_env_value(backend.endpoint_env):
        return False
    if backend.project_env and not _resolve_env_value(backend.project_env):
        return False
    return True


def _first_non_empty_env(*names: str) -> str:
    for name in names:
        value = _resolve_env_value(name)
        if value:
            return value
    return ""


def _redis_settings_from_url(redis_url: str) -> Dict[str, Any]:
    if not redis_url:
        return {}

    parsed = urlparse(redis_url)
    if parsed.scheme not in {"redis", "rediss"}:
        return {}

    if not parsed.hostname:
        return {}

    settings: Dict[str, Any] = {"redis_host": parsed.hostname}
    if parsed.port is not None:
        settings["redis_port"] = parsed.port
    if parsed.password:
        settings["redis_password"] = parsed.password
    if parsed.path and parsed.path != "/":
        try:
            settings["redis_db"] = int(parsed.path.lstrip("/"))
        except ValueError:
            pass
    return settings


def _router_redis_settings() -> Dict[str, Any]:
    redis_url = _first_non_empty_env("UPSTASH_REDIS_URL", "REDIS_URL")
    settings: Dict[str, Any] = {}

    host = _first_non_empty_env("UPSTASH_REDIS_HOST", "REDIS_HOST")
    password = _first_non_empty_env("UPSTASH_REDIS_PASSWORD", "REDIS_PASSWORD")

    if host:
        settings["redis_host"] = host
    if password:
        settings["redis_password"] = password

    port = _first_non_empty_env("UPSTASH_REDIS_PORT", "REDIS_PORT")
    if port:
        try:
            settings["redis_port"] = int(port)
        except ValueError:
            pass

    db = _first_non_empty_env("UPSTASH_REDIS_DB", "REDIS_DB")
    if db:
        try:
            settings["redis_db"] = int(db)
        except ValueError:
            pass

    if redis_url:
        parsed_settings = _redis_settings_from_url(redis_url)
        for key, value in parsed_settings.items():
            settings.setdefault(key, value)

    return settings


def _env_float(name: str, default: float = 0.0) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


async def _router_reason_cost_guard() -> Dict[str, Any]:
    cap_usd = _env_float(_ROUTER_REASON_KILL_SWITCH_ENV, 0.0)
    if cap_usd <= 0.0:
        return {"enabled": False, "cap_usd": 0.0, "current_spend_usd": 0.0, "disabled": False}

    current_spend_usd = await usage_event_store.get_total_spend_for_date(date.today())
    disabled = current_spend_usd >= cap_usd
    return {
        "enabled": True,
        "cap_usd": cap_usd,
        "current_spend_usd": current_spend_usd,
        "disabled": disabled,
    }


def _fallback_entries(logical_model: str, targets: List[str]) -> List[Dict[str, List[str]]]:
    cleaned = [target for target in targets if str(target).strip()]
    if not cleaned:
        return []
    return [{logical_model: cleaned}]


def _router_init_kwargs(
    logical_model: str,
    group: RouterModelGroup,
    model_list: List[Dict[str, Any]],
) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "model_list": model_list,
        "routing_strategy": group.routing_strategy or "cost-based-routing",
        "num_retries": group.num_retries,
        "enable_pre_call_checks": group.enable_pre_call_checks,
        "fallbacks": _fallback_entries(logical_model, group.fallbacks),
        "context_window_fallbacks": _fallback_entries(
            logical_model, group.context_window_fallbacks
        ),
        "content_policy_fallbacks": _fallback_entries(
            logical_model, group.content_policy_fallbacks
        ),
    }
    kwargs.update(_router_redis_settings())
    return kwargs


def summarize_router_models(provider_toml: Optional[ProviderToml] = None) -> List[Dict[str, Any]]:
    summaries: List[Dict[str, Any]] = []
    for model_name, group in _router_config(provider_toml).items():
        enabled_backends = [backend for backend in group.backends if _backend_is_available(backend)]
        summaries.append(
            {
                "name": model_name,
                "provider_id": ROUTER_PROVIDER_ID,
                "provider": ROUTER_PROVIDER_ID,
                "description": group.description,
                "routing_strategy": group.routing_strategy,
                "num_retries": group.num_retries,
                "enable_pre_call_checks": group.enable_pre_call_checks,
                "fallbacks": list(group.fallbacks),
                "context_window_fallbacks": list(group.context_window_fallbacks),
                "content_policy_fallbacks": list(group.content_policy_fallbacks),
                "health": "healthy" if enabled_backends else "unconfigured",
                "configured": bool(enabled_backends),
                "is_selectable": bool(enabled_backends),
                "health_reason": None if enabled_backends else "No configured router backends",
                "backends": [
                    {
                        "provider_id": backend.provider_id,
                        "litellm_provider": backend.litellm_provider,
                        "model": backend.model,
                        "order": backend.order,
                        "weight": backend.weight,
                        "cost_input_per1k": backend.cost_input_per1k,
                        "cost_output_per1k": backend.cost_output_per1k,
                        "enabled": backend.enabled,
                    }
                    for backend in group.backends
                ],
            }
        )
    return summaries


def _backend_weight(backend: RouterBackend) -> float:
    if backend.weight > 0:
        return backend.weight
    total_cost = backend.cost_input_per1k + backend.cost_output_per1k
    if total_cost <= 0:
        return 1.0
    return 1.0 / total_cost


def build_model_list(provider_toml: Optional[ProviderToml] = None) -> List[Dict[str, Any]]:
    model_list: List[Dict[str, Any]] = []
    for model_name, group in _router_config(provider_toml).items():
        for backend in group.backends:
            if not _backend_is_available(backend):
                continue

            litellm_model = f"{backend.litellm_provider}/{backend.model}"
            litellm_params: Dict[str, Any] = {
                "model": litellm_model,
                "weight": _backend_weight(backend),
            }

            api_key = _resolve_env_value(backend.api_key_env)
            if api_key:
                litellm_params["api_key"] = api_key

            api_base = _resolve_env_value(backend.endpoint_env)
            if api_base:
                litellm_params["api_base"] = api_base
            if backend.provider_id == "dashscope":
                logger.warning(
                    "DEBUG_TRACE_dashscope_api_base",
                    endpoint_env=backend.endpoint_env,
                    api_base=api_base,
                    api_base_repr=repr(api_base),
                )

            if backend.litellm_provider == "vertex_ai":
                vertex_project = _resolve_env_value(backend.project_env)
                if vertex_project:
                    litellm_params["vertex_project"] = vertex_project

                vertex_location = _resolve_vertex_location(backend)
                if vertex_location:
                    litellm_params["vertex_location"] = vertex_location

                vertex_credentials = _resolve_vertex_credentials(backend)
                if vertex_credentials:
                    litellm_params["vertex_credentials"] = vertex_credentials

            if backend.order > 0:
                litellm_params["order"] = backend.order

            model_list.append(
                {
                    "model_name": model_name,
                    "litellm_params": litellm_params,
                    "model_info": {
                        "logical_model": model_name,
                        "provider_id": backend.provider_id,
                        "backend_model": backend.model,
                        "litellm_model": litellm_model,
                        "cost_input_per1k": backend.cost_input_per1k,
                        "cost_output_per1k": backend.cost_output_per1k,
                    },
                }
            )
    return model_list


def _build_router(
    logical_model: str,
    provider_toml: Optional[ProviderToml] = None,
) -> Any:
    router_cls = _load_router_class()
    if router_cls is None:
        return None

    group = get_router_model_group(logical_model, provider_toml)
    if group is None:
        return None

    model_list = build_model_list(provider_toml)
    if not model_list:
        return None

    return router_cls(**_router_init_kwargs(logical_model, group, model_list))


@lru_cache(maxsize=None)
def _get_router(logical_model: str) -> Any:
    return _build_router(logical_model)


def invalidate_router_cache() -> None:
    _get_router.cache_clear()


def _request_kwargs(payload: Dict[str, Any], *, stream: bool, timeout_ms: int) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        key: value for key, value in payload.items() if key in _COMMON_REQUEST_KEYS
    }
    kwargs["stream"] = stream
    kwargs["timeout"] = max(timeout_ms / 1000.0, 0.1)
    return kwargs


def _response_model_name(response: Any, fallback: str) -> str:
    if isinstance(response, dict):
        model = str(response.get("model") or "").strip()
        return model or fallback
    model = str(getattr(response, "model", "") or "").strip()
    return model or fallback


def _response_usage(response: Any) -> Dict[str, Any]:
    usage: Any = None
    if isinstance(response, dict):
        usage = response.get("usage")
    else:
        usage = getattr(response, "usage", None)

    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        try:
            return dict(usage.model_dump())
        except Exception:
            return {}
    if isinstance(usage, dict):
        return dict(usage)
    if hasattr(usage, "__dict__"):
        return {key: value for key, value in vars(usage).items() if not key.startswith("_")}
    return {}


def _response_text(response: Any) -> str:
    if isinstance(response, dict):
        if response.get("choices"):
            try:
                return str(response["choices"][0]["message"]["content"] or "")
            except Exception:
                pass
        if response.get("result") and isinstance(response["result"], dict):
            text = response["result"].get("text")
            if text is not None:
                return str(text)
    choices = getattr(response, "choices", None)
    if choices:
        try:
            first = choices[0]
            message = getattr(first, "message", None)
            if message is not None and getattr(message, "content", None) is not None:
                return str(message.content)
            delta = getattr(first, "delta", None)
            if delta is not None and getattr(delta, "content", None) is not None:
                return str(delta.content)
            if getattr(first, "text", None) is not None:
                return str(first.text)
        except Exception:
            pass
    if hasattr(response, "text"):
        return str(getattr(response, "text"))
    return ""


async def _iterate_chunks(response: Any) -> AsyncGenerator[Dict[str, Any], None]:
    if response is None:
        return
    if hasattr(response, "__aiter__"):
        async for chunk in response:
            text = _response_text(chunk)
            if text:
                yield {"text": text, "raw": chunk}
        return
    if inspect.isawaitable(response):
        awaited = await response
        async for chunk in _iterate_chunks(awaited):
            yield chunk
        return
    for chunk in response:
        text = _response_text(chunk)
        if text:
            yield {"text": text, "raw": chunk}


def _selected_backend(
    response: Any, logical_model: str, provider_toml: Optional[ProviderToml] = None
) -> RouterBackend | None:
    response_model = _response_model_name(response, "")
    if response_model:
        response_model = response_model.split("/", 1)[-1]
        group = get_router_model_group(logical_model, provider_toml)
        if group is not None:
            for backend in group.backends:
                if backend.model == response_model:
                    return backend

        for candidate_group in _router_config(provider_toml).values():
            for backend in candidate_group.backends:
                if backend.model == response_model:
                    return backend

    group = get_router_model_group(logical_model, provider_toml)
    if group is None:
        return None

    for backend in group.backends:
        if _backend_is_available(backend):
            return backend
    return group.backends[0] if group.backends else None


async def _persist_routing_audit(payload: Dict[str, Any], response: Dict[str, Any]) -> None:
    routing = response.get("routing") if isinstance(response, dict) else {}
    result = response.get("result") if isinstance(response, dict) else {}
    usage = result.get("usage") if isinstance(result, dict) else {}
    classifier = routing.get("task_routing") if isinstance(routing, dict) else {}

    prompt_tokens = (
        int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        if isinstance(usage, dict)
        else 0
    )
    completion_tokens = (
        int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        if isinstance(usage, dict)
        else 0
    )
    total_tokens = prompt_tokens + completion_tokens
    cost_usd = 0.0
    backend_provider_id = routing.get("backend_provider_id") if isinstance(routing, dict) else None
    backend_litellm_model = (
        routing.get("backend_litellm_model") if isinstance(routing, dict) else None
    )
    backend_model = str(response.get("model") or "") if isinstance(response, dict) else ""
    if backend_provider_id:
        try:
            from ..providers.pricing import estimate_cost  # noqa: PLC0415

            cost_usd = estimate_cost(
                str(backend_provider_id),
                prompt_tokens,
                completion_tokens,
                model=backend_model or None,
            )
        except Exception:
            cost_usd = 0.0

    classifier_backend_litellm_model = ""
    classifier_prompt_tokens = 0
    classifier_completion_tokens = 0
    classifier_cost_usd = 0.0
    classifier_source = "router"
    classifier_confidence = 0.0
    classifier_reason = None
    task_class = "chat"
    logical_model = str(routing.get("logical_model") or response.get("provider") or "")
    if isinstance(classifier, dict):
        classifier_backend_litellm_model = str(
            classifier.get("classifier_backend_litellm_model") or ""
        )
        classifier_prompt_tokens = int(classifier.get("classifier_prompt_tokens") or 0)
        classifier_completion_tokens = int(classifier.get("classifier_completion_tokens") or 0)
        classifier_cost_usd = float(classifier.get("classifier_cost_usd") or 0.0)
        classifier_source = str(classifier.get("classifier_source") or classifier_source)
        classifier_confidence = float(classifier.get("classifier_confidence") or 0.0)
        classifier_reason = classifier.get("classifier_reason")
        task_class = str(classifier.get("task_class") or task_class)

    metadata = {
        "routing": routing,
        "backend_litellm_model": backend_litellm_model,
        "final_prompt_tokens": prompt_tokens,
        "final_completion_tokens": completion_tokens,
        "final_total_tokens": total_tokens,
        "final_cost_usd": round(cost_usd, 8),
    }
    if classifier_backend_litellm_model:
        metadata["classifier_backend_litellm_model"] = classifier_backend_litellm_model

    try:
        from ..services.task_routing_audit import record_task_routing_decision  # noqa: PLC0415

        request_id = str(payload.get("request_id") or "")
        await record_task_routing_decision(
            request_id=request_id,
            requested_model=payload.get("model") if isinstance(payload.get("model"), str) else None,
            task_class=task_class,
            classifier_source=classifier_source,
            classifier_confidence=classifier_confidence,
            classifier_reason=str(classifier_reason) if classifier_reason is not None else None,
            classifier_model=classifier_backend_litellm_model or None,
            logical_model=logical_model,
            backend_provider_id=str(backend_provider_id) if backend_provider_id else None,
            backend_model=backend_model or None,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            classifier_prompt_tokens=classifier_prompt_tokens,
            classifier_completion_tokens=classifier_completion_tokens,
            classifier_cost_usd=classifier_cost_usd,
            latency_ms=float(response.get("routing_latency_ms") or 0.0),
            success=bool(response.get("ok")),
            error_message=str(response.get("error") or "") or None,
            metadata=metadata,
        )
    except Exception as exc:  # noqa: BLE001
        # Persistence is best-effort; routing must never depend on it.
        logger.debug("task_routing_audit_persistence_failed", error=str(exc))


async def route_logical_model(
    model: Optional[str],
    payload: Dict[str, Any],
    *,
    timeout_ms: int,
    stream: bool = False,
    provider_toml: Optional[ProviderToml] = None,
    persist: bool = True,
) -> Optional[Dict[str, Any]]:
    logical_model = str(model or "").strip()
    task_route: Optional[TaskRouteDecision] = None
    if (
        logical_model not in _router_config(provider_toml)
        and logical_model not in _AUTO_MODEL_NAMES
    ):
        return None
    if logical_model in _AUTO_MODEL_NAMES:
        task_route = await resolve_task_route(
            payload,
            requested_model=logical_model or None,
            timeout_ms=timeout_ms,
            provider_toml=provider_toml,
        )
        logical_model = task_route.logical_model

    cost_guard = await _router_reason_cost_guard()
    if logical_model == "router-reason" and cost_guard.get("disabled"):
        record_router_cost_guard_event(
            logical_model="router-reason",
            action="disabled",
            cap_usd=float(cost_guard.get("cap_usd") or 0.0),
            current_spend_usd=float(cost_guard.get("current_spend_usd") or 0.0),
        )
        if task_route is not None:
            task_route = replace(task_route, logical_model=_ROUTER_REASON_FALLBACK_MODEL)
        logical_model = _ROUTER_REASON_FALLBACK_MODEL
    elif cost_guard.get("enabled"):
        record_router_cost_guard_event(
            logical_model=logical_model,
            action="checked",
            cap_usd=float(cost_guard.get("cap_usd") or 0.0),
            current_spend_usd=float(cost_guard.get("current_spend_usd") or 0.0),
        )

    router = (
        _build_router(logical_model, provider_toml)
        if provider_toml is not None
        else _get_router(logical_model)
    )
    if router is None:
        response = {
            "ok": False,
            "provider": logical_model,
            "model": logical_model,
            "error": "litellm-router-unavailable",
            "error_category": "unknown",
            "routing": {
                "logical_model": logical_model,
                "task_routing": task_route.to_metadata() if task_route else None,
            },
        }
        if persist:
            await _persist_routing_audit(payload, response)
        return response

    kwargs = _request_kwargs(payload, stream=stream, timeout_ms=timeout_ms)
    started_at = time.perf_counter()
    try:
        response = await router.acompletion(model=logical_model, **kwargs)
    except Exception as exc:
        response = {
            "ok": False,
            "provider": logical_model,
            "model": logical_model,
            "error": str(exc),
            "error_category": "unknown",
            "routing": {
                "logical_model": logical_model,
                "task_routing": task_route.to_metadata() if task_route else None,
            },
        }
        if persist:
            await _persist_routing_audit(payload, response)
        return response

    backend = _selected_backend(response, logical_model, provider_toml)
    backend_model = (
        backend.model
        if backend
        else (_response_model_name(response, logical_model) or logical_model)
    )

    response_routing: Dict[str, Any] = {
        "logical_model": logical_model,
        "backend_provider_id": backend.provider_id if backend else None,
        "backend_litellm_model": (
            f"{backend.litellm_provider}/{backend.model}" if backend else None
        ),
        "routing_latency_ms": round((time.perf_counter() - started_at) * 1000.0, 2),
        "cost_control": cost_guard,
    }
    if task_route is not None:
        response_routing["task_routing"] = task_route.to_metadata()

    if stream:
        response = {
            "ok": True,
            "provider": logical_model,
            "model": backend_model,
            "stream": _iterate_chunks(response),
            "routing": response_routing,
        }
        if persist:
            await _persist_routing_audit(payload, response)
        return response

    text = _response_text(response)
    usage = _response_usage(response)
    result = {
        "ok": True,
        "provider": logical_model,
        "model": backend_model,
        "result": {
            "text": text,
            "usage": usage,
        },
        "routing": response_routing,
    }
    if persist:
        await _persist_routing_audit(payload, result)
    return result
