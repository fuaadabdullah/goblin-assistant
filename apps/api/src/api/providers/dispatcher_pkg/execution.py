from __future__ import annotations

import asyncio
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
from ..supabase_events import check_provider_access, insert_routing_audit

try:
    from ddtrace import tracer as _dd_tracer
except ImportError:
    _dd_tracer = None  # type: ignore[assignment]


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
    from ...routing.router import registry

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
        registry.record_success(provider_id, latency_ms=latency, cost_usd=0.0)
        dispatcher.note_provider_result(provider_id, ok=True, latency_ms=latency)
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
        registry.record_failure(provider_id)
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
    from ...routing.router import registry

    resolved_pid, resolved_model = dispatcher._resolve_model_alias(pid, model)
    user_id: Optional[str] = payload.get("user_id") or None
    messages = payload.get("messages", [])
    prompt = payload.get("prompt", "")
    candidates = dispatcher._candidate_order(resolved_pid)
    if not candidates:
        try:
            if dispatcher.is_configured("mock") and dispatcher._ensure_provider("mock") is not None:
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
            return {
                "ok": False,
                "error": f"unknown-provider:{pid}",
                "latency_ms": 0.0,
            }

    explicit_mode = resolved_pid not in (None, "auto", "cheapest", "local")
    if explicit_mode:
        first_config = dispatcher._configs.get(candidates[0], {}) if candidates else {}
        if first_config.get("force_fallback"):
            fallback_order = [p for p in dispatcher._hybrid_order() if p not in candidates]
            ordered = [*candidates, *fallback_order]
        else:
            ordered = candidates
    else:
        configured_candidates = dispatcher._auto_configured_candidates(candidates)
        if not configured_candidates:
            configured_candidates = [p for p in candidates if dispatcher.is_configured(p)]

        available: List[str] = []
        for provider_id in configured_candidates:
            current_provider = dispatcher._ensure_provider(provider_id)
            if current_provider is None:
                continue
            canary = dispatcher._is_canary_attempt(provider_id, resolved_model)
            if current_provider.should_attempt(canary=canary) and (
                registry.get(provider_id).success_rate >= dispatcher._routing_min_success_rate
            ):
                available.append(provider_id)
        ordered = available or configured_candidates

    if explicit_mode and not ordered:
        ordered = candidates
    if not ordered:
        mock_provider = None
        try:
            if dispatcher.is_configured("mock"):
                mock_provider = dispatcher._ensure_provider("mock")
        except Exception:
            mock_provider = None

        if mock_provider is not None:
            ordered = ["mock"]
        else:
            return {
                "ok": False,
                "error": "no-configured-providers",
                "latency_ms": 0.0,
            }

    if user_id:
        allowed = [p for p in ordered if await check_provider_access(user_id, p)]
        if not allowed:
            return {
                "ok": False,
                "error": "provider-access-denied",
                "latency_ms": 0.0,
            }
        ordered = allowed

    if dry_run:
        candidate_detail = []
        for provider_id in ordered:
            current_provider = dispatcher._ensure_provider(provider_id)
            candidate_detail.append(
                {
                    "provider": provider_id,
                    "model": resolved_model
                    or (current_provider.default_model if current_provider else ""),
                    "configured": dispatcher.is_configured(provider_id),
                }
            )
        first = candidate_detail[0]
        return {
            "ok": True,
            "dry_run": True,
            "resolved_provider": first["provider"],
            "resolved_model": first["model"],
            "routing_mode": "explicit" if explicit_mode else "auto",
            "candidate_order": candidate_detail,
        }

    last_error = "all providers failed"
    last_category: Optional[ProviderErrorCategory] = None
    _attempted: List[str] = []
    _routing_mode = "explicit" if explicit_mode else resolved_pid or "auto"

    _req_ctx = (
        _dd_tracer.trace(
            "dispatch.request",
            resource=f"{_routing_mode}/{resolved_model or 'any'}",
            service="goblin-api",
            span_type="web",
        )
        if _dd_tracer
        else nullcontext()
    )
    with _req_ctx as rspan:
        _tag(rspan, "dispatch.routing_mode", _routing_mode)
        _tag(rspan, "dispatch.pid", pid or "auto")
        _tag(rspan, "dispatch.model", resolved_model or "")
        _tag(rspan, "dispatch.stream", stream)
        _tag(rspan, "dispatch.candidates", len(ordered))

        for provider_id in ordered:
            current_provider = dispatcher._ensure_provider(provider_id)
            if current_provider is None:
                continue

            model_name = resolved_model or current_provider.default_model
            log = logger.bind(provider=provider_id, model=model_name)
            _attempted.append(provider_id)

            _att_ctx = (
                _dd_tracer.trace(
                    "dispatch.attempt",
                    resource=provider_id,
                    service="goblin-api",
                )
                if _dd_tracer
                else nullcontext()
            )
            with _att_ctx as aspan:
                _tag(aspan, "provider.id", provider_id)
                _tag(aspan, "provider.model", model_name)

                if dispatcher._is_warmup_routing_blocked(provider_id):
                    last_error = "provider warming up"
                    last_category = ProviderErrorCategory.SERVER_ERROR
                    _tag(aspan, "dispatch.skip_reason", "warmup")
                    log.info(
                        "dispatch_warmup_skipped",
                        warmup=dispatcher._warmup_state_for(provider_id),
                    )
                    continue
                canary = dispatcher._is_canary_attempt(provider_id, model_name)
                if not current_provider.should_attempt(canary=canary):
                    last_error = "provider circuit open"
                    last_category = ProviderErrorCategory.SERVER_ERROR
                    _tag(aspan, "dispatch.skip_reason", "circuit_open")
                    log.info(
                        "dispatch_circuit_skipped",
                        circuit_state=current_provider.circuit_state,
                    )
                    continue
                if current_provider.circuit_state == "soft_open":
                    if not current_provider.claim_soft_open_probe():
                        last_error = "provider circuit open"
                        last_category = ProviderErrorCategory.SERVER_ERROR
                        _tag(
                            aspan,
                            "dispatch.skip_reason",
                            "soft_open_probe_denied",
                        )
                        log.info(
                            "dispatch_circuit_skipped",
                            circuit_state=current_provider.circuit_state,
                        )
                        continue
                kwargs = dispatcher._build_invoke_kwargs(payload)
                reservation = await quota_service.reserve(
                    provider_id,
                    model_name,
                    messages=messages,
                    prompt=prompt,
                    max_tokens=int(payload.get("max_tokens", 0) or 0) or None,
                )
                if reservation is None:
                    last_error = "quota exhausted"
                    last_category = ProviderErrorCategory.RATE_LIMIT
                    _tag(aspan, "dispatch.skip_reason", "quota_exhausted")
                    log.info(
                        "dispatch_quota_skipped",
                        reason=quota_service.last_skip_reason,
                    )
                    continue

                log.info("dispatch_attempt")

                try:
                    if stream:
                        result = await asyncio.wait_for(
                            dispatcher._stream_wrap(
                                provider_id,
                                current_provider,
                                messages,
                                model_name,
                                prompt=prompt,
                                **kwargs,
                            ),
                            timeout=timeout_ms / 1000,
                        )
                        if result.ok:
                            _tag(aspan, "dispatch.outcome", "success")
                            _tag(rspan, "dispatch.final_provider", provider_id)
                            await quota_service.commit(
                                reservation,
                                actual_input_tokens=(reservation.estimated_input_tokens),
                                actual_output_tokens=(reservation.estimated_output_tokens),
                            )
                            return {
                                "ok": True,
                                "stream": result.raw.get("stream_gen"),
                                "provider": provider_id,
                                "model": model_name,
                            }
                        await quota_service.release(reservation)
                        last_error = dispatcher._sanitize_error(result.error or last_error)
                        last_category = dispatcher._provider_error_category(
                            result.error_category,
                            last_error,
                        )
                        _tag(aspan, "dispatch.outcome", "failure")
                        _tag(
                            aspan,
                            "error.category",
                            last_category.value if last_category else "",
                        )
                        if last_category == ProviderErrorCategory.RATE_LIMIT:
                            await quota_service.mark_rate_limited(provider_id, model_name)
                        continue

                    result = await asyncio.wait_for(
                        dispatcher._invoke_with_test_mode(
                            provider_id,
                            current_provider,
                            messages,
                            model_name,
                            prompt=prompt,
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
                        registry.record_success(
                            provider_id,
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
                        _tag(
                            aspan,
                            "dispatch.latency_ms",
                            round(float(result.latency_ms), 1),
                        )
                        _tag(rspan, "dispatch.final_provider", provider_id)
                        log.info(
                            "dispatch_success",
                            latency_ms=round(float(result.latency_ms), 1),
                        )
                        usage = result.usage or {}
                        insert_routing_audit(
                            payload.get("request_id", ""),
                            model_name,
                            user_id=user_id,
                            routing_mode=_routing_mode,
                            selected_provider=provider_id,
                            attempted_providers=_attempted,
                            latency_ms=int(result.latency_ms),
                            input_tokens=int(
                                usage.get("prompt_tokens") or usage.get("input_tokens") or 0
                            )
                            or None,
                            output_tokens=int(
                                usage.get("completion_tokens") or usage.get("output_tokens") or 0
                            )
                            or None,
                            cost_usd=float(result.cost_usd or 0) or None,
                            success=True,
                        )
                        return result.to_dict()

                    await quota_service.release(reservation)
                    last_error = dispatcher._sanitize_error(result.error or last_error)
                    last_category = dispatcher._provider_error_category(
                        result.error_category,
                        last_error,
                    )
                    await _record_provider_failure(
                        provider_id,
                        current_provider,
                        last_error,
                        category=last_category,
                    )
                    registry.record_failure(provider_id)
                    dispatcher.note_provider_result(provider_id, ok=False, error=last_error)
                    if last_category == ProviderErrorCategory.RATE_LIMIT:
                        await quota_service.mark_rate_limited(provider_id, model_name)
                    record_dispatch(
                        provider_id=provider_id,
                        model=model_name,
                        latency_ms=float(result.latency_ms),
                        ok=False,
                        error_category=result.error_category,
                    )
                    _tag(aspan, "dispatch.outcome", "failure")
                    _tag(aspan, "error.category", result.error_category or "")
                    log.warning(
                        "dispatch_failure",
                        error=last_error,
                        error_category=result.error_category,
                    )
                except asyncio.TimeoutError:
                    await quota_service.release(reservation)
                    last_error = f"timeout after {timeout_ms}ms"
                    last_category = ProviderErrorCategory.TIMEOUT
                    await _record_provider_failure(
                        provider_id,
                        current_provider,
                        last_error,
                        category=last_category,
                    )
                    registry.record_failure(provider_id)
                    dispatcher.note_provider_result(provider_id, ok=False, error=last_error)
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
                        "dispatch_timeout",
                        error=last_error,
                        error_category=ProviderErrorCategory.TIMEOUT.value,
                        latency_ms=timeout_ms,
                    )
                except Exception as exc:
                    await quota_service.release(reservation)
                    last_error = dispatcher._sanitize_error(exc)
                    last_category = classify_provider_error(exc)
                    await _record_provider_failure(
                        provider_id,
                        current_provider,
                        last_error,
                        category=last_category,
                    )
                    registry.record_failure(provider_id)
                    dispatcher.note_provider_result(provider_id, ok=False, error=last_error)
                    record_dispatch(
                        provider_id=provider_id,
                        model=model_name,
                        latency_ms=0.0,
                        ok=False,
                        error_category=last_category.value,
                    )
                    if last_category == ProviderErrorCategory.RATE_LIMIT:
                        await quota_service.mark_rate_limited(provider_id, model_name)
                    _tag(aspan, "dispatch.outcome", "exception")
                    _tag(aspan, "error.category", last_category.value)
                    log.warning(
                        "dispatch_exception",
                        error=last_error,
                        error_category=last_category.value,
                    )

        _tag(rspan, "dispatch.all_failed", True)
        _tag(rspan, "dispatch.error", last_error)

        insert_routing_audit(
            payload.get("request_id", ""),
            resolved_model or "",
            user_id=user_id,
            routing_mode=_routing_mode,
            attempted_providers=_attempted,
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
