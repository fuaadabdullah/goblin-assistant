from __future__ import annotations

import asyncio
import os
from contextlib import nullcontext
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from ...ops.integrations.jira import publish_circuit_breaker_incident
from ..base import (
    BaseProvider,
    ProviderErrorCategory,
    ProviderResult,
    classify_provider_error,
)
from ..metrics import record_dispatch
from ..quota_service import quota_service
from ..router_service import get_router_model_names
from ..supabase_events import insert_routing_audit
from .selection import SelectionEngine

try:
    from ddtrace.trace import tracer as _dd_tracer
except ImportError:
    _dd_tracer = None  # type: ignore[assignment]


def mock_fallback_enabled() -> bool:
    if os.getenv("ALLOW_MOCK_PROVIDER_FALLBACK", "").strip().lower() == "true":
        return True
    environment = os.getenv("ENVIRONMENT", "").strip().lower()
    return environment in {"development", "dev", "local", "test"}


def _tag(span: Any, key: str, val: Any) -> None:
    """Set a tag on a ddtrace span; silently no-ops when span is None."""
    if span is not None:
        span.set_tag(key, val)


def provider_error_category(
    value: Any,
    fallback_error: str,
) -> Optional[ProviderErrorCategory]:
    if value is None:
        return classify_provider_error(fallback_error) if fallback_error else None
    if isinstance(value, ProviderErrorCategory):
        return value
    try:
        normalized = str(value).strip().lower().replace("_", "-")
        return ProviderErrorCategory(normalized)
    except Exception:
        return classify_provider_error(fallback_error) if fallback_error else None


def build_invoke_kwargs(payload: Dict[str, Any]) -> Dict[str, Any]:
    kwargs = dict(payload)
    for key in ("messages", "prompt", "model", "user_id", "request_id", "intent"):
        kwargs.pop(key, None)
    return kwargs


async def _record_provider_failure(
    provider_id: str,
    provider: BaseProvider,
    error: str,
    *,
    category: Optional[ProviderErrorCategory | str] = None,
) -> None:
    previous_state = provider.circuit_state
    provider.record_failure(error, category=category)
    current_state = provider.circuit_state
    if current_state == previous_state or current_state not in {
        "soft_open",
        "hard_open",
    }:
        return
    await publish_circuit_breaker_incident(
        provider_id=provider_id,
        circuit_state=current_state,
        error=error,
        occurred_at=datetime.now(timezone.utc).isoformat(),
    )


async def _record_provider_observation(
    provider_id: str,
    *,
    ok: bool,
    latency_ms: float = 0.0,
    error: Optional[str] = None,
    error_category: Optional[str] = None,
) -> None:
    try:
        from ...services.provider_health import health_monitor

        await health_monitor.observe_request(
            provider_id,
            ok=ok,
            latency_ms=latency_ms,
            error=error,
            error_category=error_category,
        )
    except Exception:
        return


async def stream_wrap(
    dispatcher: Any,
    provider_id: str,
    provider: BaseProvider,
    messages: List[Dict[str, str]],
    model: str,
    *,
    logger: Any,
    **kwargs: Any,
) -> ProviderResult:
    started_at = asyncio.get_running_loop().time()
    try:
        await dispatcher._apply_test_mode_delay(provider_id)
        injected = await dispatcher._maybe_inject_test_failure(provider_id, model)
        if injected is not None:
            return injected
        gen = provider.stream(messages, model, **kwargs)
        first = None
        async for chunk in gen:
            first = chunk
            break

        async def combined() -> AsyncGenerator[Dict[str, Any], None]:
            if first is not None:
                yield first
            async for item in gen:
                yield item

        latency = (asyncio.get_running_loop().time() - started_at) * 1000
        provider.record_success()
        dispatcher.record_routing_outcome(provider_id, ok=True, latency_ms=latency, cost_usd=0.0)
        dispatcher.note_provider_result(provider_id, ok=True, latency_ms=latency)
        await _record_provider_observation(provider_id, ok=True, latency_ms=latency)
        record_dispatch(
            provider_id=provider_id,
            model=model,
            latency_ms=latency,
            ok=True,
        )
        logger.bind(
            provider=provider_id,
            model=model,
            latency_ms=round(latency, 1),
        ).info("dispatch_stream_success")
        return ProviderResult(
            ok=True,
            provider=provider_id,
            model=model,
            latency_ms=latency,
            raw={"stream_gen": combined()},
        )
    except Exception as exc:
        safe_error = dispatcher._sanitize_error(exc)
        error_category = classify_provider_error(exc).value
        await _record_provider_failure(
            provider_id,
            provider,
            safe_error,
            category=error_category,
        )
        await _record_provider_observation(
            provider_id,
            ok=False,
            error=safe_error,
            error_category=error_category,
        )
        dispatcher.record_routing_outcome(provider_id, ok=False)
        dispatcher.note_provider_result(provider_id, ok=False, error=safe_error)
        record_dispatch(
            provider_id=provider_id,
            model=model,
            latency_ms=0.0,
            ok=False,
            error_category=error_category,
        )
        logger.bind(
            provider=provider_id,
            model=model,
            error_category=error_category,
        ).warning("dispatch_stream_failure", error=safe_error)
        return ProviderResult(
            ok=False,
            provider=provider_id,
            model=model,
            error=safe_error,
            error_category=error_category,
        )


# ============================================================================
# Helper: candidate resolution
# ============================================================================


def _resolve_and_order_candidates(
    dispatcher: Any,
    resolved_pid: Optional[str],
    candidates: List[str],
) -> tuple[bool, List[str]]:
    """Compatibility wrapper for callers that still import this helper."""
    plan = SelectionEngine(dispatcher).resolve_and_order_candidates(resolved_pid, candidates)
    return plan.explicit_mode, plan.ordered


# ============================================================================
# Helper: dry-run response
# ============================================================================


def _build_dry_run_response(
    dispatcher: Any,
    ordered: List[str],
    resolved_model: Optional[str],
    explicit_mode: bool,
) -> Dict[str, Any]:
    """Compatibility wrapper for callers that still import this helper."""
    return SelectionEngine(dispatcher).build_dry_run_response(
        ordered,
        resolved_model,
        explicit_mode,
    )


# ============================================================================
# Helper: single dispatch attempt
# ============================================================================


class ProviderExecutor:
    """Executes exactly one provider attempt for an already-selected candidate."""

    def __init__(self, dispatcher: Any) -> None:
        self._dispatcher = dispatcher

    async def execute_attempt(
        self,
        *,
        provider_id: str,
        model_name: str,
        payload: Dict[str, Any],
        timeout_ms: int,
        stream: bool,
        routing_mode: str,
        rspan: Any,
        aspan: Any,
        log: Any,
        attempted: List[str],
    ) -> tuple[Optional[Dict[str, Any]], Optional[str], Optional[ProviderErrorCategory]]:
        return await _execute_dispatch_attempt_impl(
            dispatcher=self._dispatcher,
            provider_id=provider_id,
            model_name=model_name,
            payload=payload,
            timeout_ms=timeout_ms,
            stream=stream,
            routing_mode=routing_mode,
            rspan=rspan,
            aspan=aspan,
            log=log,
            attempted=attempted,
        )


async def _execute_dispatch_attempt(
    dispatcher: Any,
    provider_id: str,
    model_name: str,
    payload: Dict[str, Any],
    timeout_ms: int,
    stream: bool,
    routing_mode: str,
    rspan: Any,
    aspan: Any,
    log: Any,
    attempted: List[str],
) -> tuple[Optional[Dict[str, Any]], Optional[str], Optional[ProviderErrorCategory]]:
    """Compatibility wrapper for callers that still import this helper."""
    return await ProviderExecutor(dispatcher).execute_attempt(
        provider_id=provider_id,
        model_name=model_name,
        payload=payload,
        timeout_ms=timeout_ms,
        stream=stream,
        routing_mode=routing_mode,
        rspan=rspan,
        aspan=aspan,
        log=log,
        attempted=attempted,
    )


async def _execute_dispatch_attempt_impl(
    dispatcher: Any,
    provider_id: str,
    model_name: str,
    payload: Dict[str, Any],
    timeout_ms: int,
    stream: bool,
    routing_mode: str,
    rspan: Any,
    aspan: Any,
    log: Any,
    attempted: List[str],
) -> tuple[Optional[Dict[str, Any]], Optional[str], Optional[ProviderErrorCategory]]:
    """Execute a single dispatch attempt.

    Returns (response, error, error_category) - response is set on success.
    """
    _tag(aspan, "provider.id", provider_id)
    _tag(aspan, "provider.model", model_name)

    if dispatcher._is_warmup_routing_blocked(provider_id):
        _tag(aspan, "dispatch.skip_reason", "warmup")
        log.info("dispatch_warmup_skipped", warmup=dispatcher._warmup_state_for(provider_id))
        return None, "provider warming up", ProviderErrorCategory.SERVER_ERROR

    canary = dispatcher._is_canary_attempt(provider_id, model_name)
    if not dispatcher._ensure_provider(provider_id).should_attempt(canary=canary):
        _tag(aspan, "dispatch.skip_reason", "circuit_open")
        log.info(
            "dispatch_circuit_skipped",
            circuit_state=dispatcher._ensure_provider(provider_id).circuit_state,
        )
        return None, "provider circuit open", ProviderErrorCategory.SERVER_ERROR

    current_provider = dispatcher._ensure_provider(provider_id)
    if current_provider.circuit_state == "soft_open":
        if not current_provider.claim_soft_open_probe():
            _tag(aspan, "dispatch.skip_reason", "soft_open_probe_denied")
            log.info("dispatch_circuit_skipped", circuit_state=current_provider.circuit_state)
            return None, "provider circuit open", ProviderErrorCategory.SERVER_ERROR

    kwargs = dispatcher._build_invoke_kwargs(payload)
    reservation = await quota_service.reserve(
        provider_id,
        model_name,
        messages=payload.get("messages", []),
        prompt=payload.get("prompt", ""),
        max_tokens=int(payload.get("max_tokens", 0) or 0) or None,
    )
    if reservation is None:
        log.info("dispatch_quota_skipped", reason=quota_service.last_skip_reason)
        return None, "quota exhausted", ProviderErrorCategory.RATE_LIMIT

    log.info("dispatch_attempt")

    try:
        if stream:
            result = await asyncio.wait_for(
                dispatcher._stream_wrap(
                    provider_id,
                    current_provider,
                    payload.get("messages", []),
                    model_name,
                    prompt=payload.get("prompt", ""),
                    **kwargs,
                ),
                timeout=timeout_ms / 1000,
            )
            if result.ok:
                _tag(aspan, "dispatch.outcome", "success")
                _tag(rspan, "dispatch.final_provider", provider_id)
                await quota_service.commit(
                    reservation,
                    actual_input_tokens=reservation.estimated_input_tokens,
                    actual_output_tokens=reservation.estimated_output_tokens,
                )
                await _record_provider_observation(
                    provider_id,
                    ok=True,
                    latency_ms=float(result.latency_ms or 0.0),
                )
                return (
                    {
                        "ok": True,
                        "stream": result.raw.get("stream_gen"),
                        "provider": provider_id,
                        "model": model_name,
                    },
                    None,
                    None,
                )
            await quota_service.release(reservation)
            error_msg = result.error or "stream failed"
            error_cat = dispatcher._provider_error_category(result.error_category, error_msg)
            await _record_provider_failure(
                provider_id,
                current_provider,
                error_msg,
                category=error_cat,
            )
            await _record_provider_observation(
                provider_id,
                ok=False,
                latency_ms=float(result.latency_ms or 0.0),
                error=error_msg,
                error_category=error_cat.value if error_cat else None,
            )
            dispatcher.record_routing_outcome(provider_id, ok=False)
            dispatcher.note_provider_result(provider_id, ok=False, error=error_msg)
            record_dispatch(
                provider_id=provider_id,
                model=model_name,
                latency_ms=float(result.latency_ms or 0.0),
                ok=False,
                error_category=error_cat.value if error_cat else None,
            )
            if error_cat == ProviderErrorCategory.RATE_LIMIT:
                await quota_service.mark_rate_limited(provider_id, model_name)
            _tag(aspan, "dispatch.outcome", "soft_failure")
            if error_cat is not None:
                _tag(aspan, "error.category", error_cat.value)
            log.warning(
                "dispatch_stream_soft_failure",
                error=error_msg,
                error_category=error_cat.value if error_cat else None,
            )
            return None, error_msg, error_cat

        result = await asyncio.wait_for(
            dispatcher._invoke_with_test_mode(
                provider_id,
                current_provider,
                payload.get("messages", []),
                model_name,
                prompt=payload.get("prompt", ""),
                **kwargs,
            ),
            timeout=timeout_ms / 1000,
        )
        if result.ok:
            usage = result.usage or {}
            await quota_service.commit(
                reservation,
                actual_input_tokens=int(
                    usage.get("prompt_tokens") or usage.get("input_tokens") or 0
                ),
                actual_output_tokens=int(
                    usage.get("completion_tokens") or usage.get("output_tokens") or 0
                ),
            )
            current_provider.record_success()
            dispatcher.record_routing_outcome(
                provider_id,
                ok=True,
                latency_ms=float(result.latency_ms),
                cost_usd=float(result.cost_usd or 0.0),
            )
            dispatcher.note_provider_result(
                provider_id,
                ok=True,
                latency_ms=float(result.latency_ms),
            )
            record_dispatch(
                provider_id=provider_id,
                model=model_name,
                latency_ms=float(result.latency_ms),
                ok=True,
            )
            _tag(aspan, "dispatch.outcome", "success")
            _tag(aspan, "dispatch.latency_ms", round(float(result.latency_ms), 1))
            _tag(rspan, "dispatch.final_provider", provider_id)
            log.info("dispatch_success", latency_ms=round(float(result.latency_ms), 1))
            insert_routing_audit(
                payload.get("request_id", ""),
                model_name,
                user_id=payload.get("user_id"),
                routing_mode=routing_mode,
                selected_provider=provider_id,
                attempted_providers=attempted,
                latency_ms=int(result.latency_ms),
                input_tokens=int(
                    (result.usage or {}).get("prompt_tokens")
                    or (result.usage or {}).get("input_tokens")
                    or 0
                )
                or None,
                output_tokens=int(
                    (result.usage or {}).get("completion_tokens")
                    or (result.usage or {}).get("output_tokens")
                    or 0
                )
                or None,
                cost_usd=float(result.cost_usd or 0) or None,
                success=True,
            )
            return result.to_dict(), None, None

        await quota_service.release(reservation)
        error_msg = result.error or "provider failed"
        error_cat = dispatcher._provider_error_category(result.error_category, error_msg)
        await _record_provider_failure(
            provider_id,
            current_provider,
            error_msg,
            category=error_cat,
        )
        dispatcher.record_routing_outcome(provider_id, ok=False)
        dispatcher.note_provider_result(provider_id, ok=False, error=error_msg)
        record_dispatch(
            provider_id=provider_id,
            model=model_name,
            latency_ms=float(result.latency_ms or 0.0),
            ok=False,
            error_category=error_cat.value if error_cat else None,
        )
        if error_cat == ProviderErrorCategory.RATE_LIMIT:
            await quota_service.mark_rate_limited(provider_id, model_name)
        _tag(aspan, "dispatch.outcome", "soft_failure")
        if error_cat is not None:
            _tag(aspan, "error.category", error_cat.value)
        log.warning(
            "dispatch_soft_failure",
            error=error_msg,
            error_category=error_cat.value if error_cat else None,
        )
        return None, error_msg, error_cat

    except asyncio.TimeoutError:
        await quota_service.release(reservation)
        timeout_error = f"timeout after {timeout_ms}ms"
        await _record_provider_failure(
            provider_id, current_provider, timeout_error, category=ProviderErrorCategory.TIMEOUT
        )
        await _record_provider_observation(
            provider_id,
            ok=False,
            latency_ms=float(timeout_ms),
            error=timeout_error,
            error_category=ProviderErrorCategory.TIMEOUT.value,
        )
        dispatcher.record_routing_outcome(provider_id, ok=False)
        dispatcher.note_provider_result(provider_id, ok=False, error=timeout_error)
        record_dispatch(
            provider_id=provider_id,
            model=model_name,
            latency_ms=float(timeout_ms),
            ok=False,
            error_category=ProviderErrorCategory.TIMEOUT.value,
        )
        _tag(aspan, "dispatch.outcome", "timeout")
        _tag(aspan, "error.category", "timeout")
        log.warning(
            "dispatch_timeout", error=timeout_error, error_category="timeout", latency_ms=timeout_ms
        )
        return None, timeout_error, ProviderErrorCategory.TIMEOUT

    except Exception as exc:
        await quota_service.release(reservation)
        error_msg = dispatcher._sanitize_error(exc)
        error_cat = classify_provider_error(exc)
        await _record_provider_failure(provider_id, current_provider, error_msg, category=error_cat)
        await _record_provider_observation(
            provider_id,
            ok=False,
            error=error_msg,
            error_category=error_cat.value,
        )
        dispatcher.record_routing_outcome(provider_id, ok=False)
        dispatcher.note_provider_result(provider_id, ok=False, error=error_msg)
        record_dispatch(
            provider_id=provider_id,
            model=model_name,
            latency_ms=0.0,
            ok=False,
            error_category=error_cat.value,
        )
        if error_cat == ProviderErrorCategory.RATE_LIMIT:
            await quota_service.mark_rate_limited(provider_id, model_name)
        _tag(aspan, "dispatch.outcome", "exception")
        _tag(aspan, "error.category", error_cat.value)
        log.warning("dispatch_exception", error=error_msg, error_category=error_cat.value)
        return None, error_msg, error_cat


async def _dispatch_request_impl(
    dispatcher: Any,
    *,
    pid: Optional[str],
    model: Optional[str],
    payload: Dict[str, Any],
    timeout_ms: int = 30_000,
    stream: bool = False,
    dry_run: bool = False,
    logger: Any,
    selection_engine: Optional[SelectionEngine] = None,
    provider_executor: Optional[ProviderExecutor] = None,
) -> Dict[str, Any]:
    """Dispatch a request to a provider with fallback support."""
    selection_engine = selection_engine or SelectionEngine(dispatcher)
    provider_executor = provider_executor or ProviderExecutor(dispatcher)
    logical_model_names = set(get_router_model_names())
    should_route_logical = bool(model) and str(model).strip() in (
        logical_model_names | {"auto", "cheapest", "local"}
    )
    if should_route_logical:
        from ...providers.router_service import route_logical_model

        router_response = await route_logical_model(
            model, payload, timeout_ms=timeout_ms, stream=stream
        )
        if router_response is not None:
            return router_response

    resolved_pid, resolved_model = dispatcher._resolve_model_alias(pid, model)
    candidates = dispatcher._candidate_order(resolved_pid)

    # Handle empty candidates with mock fallback
    if not candidates:
        try:
            if (
                mock_fallback_enabled()
                and dispatcher.is_configured("mock")
                and dispatcher._ensure_provider("mock") is not None
            ):
                candidates = ["mock"]
                logger.warning(
                    "dispatch_mock_fallback",
                    routing_mode="auto"
                    if resolved_pid in (None, "auto", "cheapest", "local")
                    else "explicit",
                    provider_id=pid or "auto",
                    model=resolved_model or "",
                )
        except Exception:
            candidates = []
        if not candidates:
            return {"ok": False, "error": f"unknown-provider:{pid}", "latency_ms": 0.0}

    selection_plan = selection_engine.resolve_and_order_candidates(resolved_pid, candidates)
    explicit_mode = selection_plan.explicit_mode
    ordered = selection_plan.ordered

    # Apply filters: explicit mode fallback, mock fallback, access control
    if explicit_mode and not ordered:
        ordered = candidates
    if not ordered:
        try:
            if mock_fallback_enabled() and dispatcher.is_configured("mock"):
                mock_provider = dispatcher._ensure_provider("mock")
                if mock_provider is not None:
                    ordered = ["mock"]
        except Exception:
            pass
        if not ordered:
            return {"ok": False, "error": "no-configured-providers", "latency_ms": 0.0}

    allowed = await selection_engine.apply_user_access(ordered, user_id=payload.get("user_id"))
    if not allowed and ordered:
        return {"ok": False, "error": "provider-access-denied", "latency_ms": 0.0}
    ordered = allowed

    if dry_run:
        return selection_engine.build_dry_run_response(ordered, resolved_model, explicit_mode)

    last_error = "all providers failed"
    last_category: Optional[ProviderErrorCategory] = None
    attempted: List[str] = []
    routing_mode = selection_plan.routing_mode

    req_ctx = (
        _dd_tracer.trace(
            "dispatch.request",
            resource=f"{routing_mode}/{resolved_model or 'any'}",
            service="goblin-api",
            span_type="web",
        )
        if _dd_tracer
        else nullcontext()
    )
    with req_ctx as rspan:
        _tag(rspan, "dispatch.routing_mode", routing_mode)
        _tag(rspan, "dispatch.pid", pid or "auto")
        _tag(rspan, "dispatch.model", resolved_model or "")
        _tag(rspan, "dispatch.stream", stream)
        _tag(rspan, "dispatch.candidates", len(ordered))

        for provider_id in ordered:
            current_provider = dispatcher._ensure_provider(provider_id)
            if current_provider is None:
                continue

            attempted.append(provider_id)
            log = logger.bind(provider=provider_id, model=resolved_model or "")

            att_ctx = (
                _dd_tracer.trace("dispatch.attempt", resource=provider_id, service="goblin-api")
                if _dd_tracer
                else nullcontext()
            )
            with att_ctx as aspan:
                response, err, cat = await provider_executor.execute_attempt(
                    provider_id=provider_id,
                    model_name=resolved_model or current_provider.default_model,
                    payload=payload,
                    timeout_ms=timeout_ms,
                    stream=stream,
                    routing_mode=routing_mode,
                    rspan=rspan,
                    aspan=aspan,
                    log=log,
                    attempted=attempted,
                )
                if response is not None:
                    return response
                last_error = err or "provider failed"
                last_category = cat

        _tag(rspan, "dispatch.all_failed", True)
        _tag(rspan, "dispatch.error", last_error)

        insert_routing_audit(
            payload.get("request_id", ""),
            resolved_model or "",
            user_id=payload.get("user_id"),
            routing_mode=routing_mode,
            attempted_providers=attempted,
            success=False,
            error_message=last_error,
            error_category=last_category.value if last_category else None,
        )
        return {
            "ok": False,
            "error": last_error,
            "error_category": last_category.value if last_category else None,
            "provider": "none",
            "latency_ms": 0.0,
        }


class ExecutionEngine:
    """Coordinates request execution after selection ownership is delegated."""

    def __init__(
        self,
        dispatcher: Any,
        *,
        logger: Any,
        selection_engine: Optional[SelectionEngine] = None,
        provider_executor: Optional[ProviderExecutor] = None,
    ) -> None:
        self._dispatcher = dispatcher
        self._logger = logger
        self._selection_engine = selection_engine or SelectionEngine(dispatcher)
        self._provider_executor = provider_executor or ProviderExecutor(dispatcher)

    async def dispatch(
        self,
        *,
        pid: Optional[str],
        model: Optional[str],
        payload: Dict[str, Any],
        timeout_ms: int = 30_000,
        stream: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        return await _dispatch_request_impl(
            self._dispatcher,
            pid=pid,
            model=model,
            payload=payload,
            timeout_ms=timeout_ms,
            stream=stream,
            dry_run=dry_run,
            logger=self._logger,
            selection_engine=self._selection_engine,
            provider_executor=self._provider_executor,
        )


async def dispatch_request(
    dispatcher: Any,
    *,
    pid: Optional[str],
    model: Optional[str],
    payload: Dict[str, Any],
    timeout_ms: int = 30_000,
    stream: bool = False,
    dry_run: bool = False,
    logger: Any,
) -> Dict[str, Any]:
    """Compatibility wrapper for callers that still import this helper."""
    return await ExecutionEngine(dispatcher, logger=logger).dispatch(
        pid=pid,
        model=model,
        payload=payload,
        timeout_ms=timeout_ms,
        stream=stream,
        dry_run=dry_run,
    )
