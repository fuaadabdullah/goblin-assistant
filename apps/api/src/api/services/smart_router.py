"""
Compatibility smart-router facade backed by the authoritative dispatcher.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from api.providers.dispatcher import canonical_provider_id, dispatcher
from api.providers.pricing import resolve_model_pricing
from api.routing.router import (
    cost_router,
    hybrid_router,
    latency_router,
    registry,
    tier_router,
    top_providers_for,
)

from .provider_health import health_monitor


def _provider_pricing(provider: Any) -> ProviderCost:
    config = getattr(provider, "config", None)
    if isinstance(config, dict):
        pricing = resolve_model_pricing(
            getattr(provider, "provider_id", ""),
            getattr(provider, "default_model", None) or None,
            config=config,
        )
        return ProviderCost(input_cost=pricing.input_per1k, output_cost=pricing.output_per1k)

    return ProviderCost(input_cost=0.0, output_cost=0.0)


class TaskType(Enum):
    CHAT = "chat"
    CODE_GENERATION = "code"
    CODE_REVIEW = "code_review"
    REASONING = "reasoning"
    SUMMARIZATION = "summary"
    EMBEDDING = "embedding"
    IMAGE_GENERATION = "image"
    VISION = "vision"
    TRANSLATION = "translation"


class RoutingStrategy(Enum):
    COST_OPTIMIZED = "cost_optimized"
    QUALITY_FIRST = "quality_first"
    LATENCY_OPTIMIZED = "latency_optimized"
    BALANCED = "balanced"
    LOCAL_FIRST = "local_first"
    ML_BANDIT = "ml_bandit"


@dataclass
class ProviderCost:
    input_cost: float
    output_cost: float

    def estimate(self, input_tokens: int, output_tokens: int) -> float:
        return input_tokens / 1000 * self.input_cost + output_tokens / 1000 * self.output_cost


@dataclass
class ProviderSelection:
    provider_id: str
    model: str
    reason: str
    fallback_chain: List[str]
    estimated_cost: float
    expected_latency_ms: float


class CostTracker:
    def __init__(self, hourly_budget: float = 10.0) -> None:
        self.hourly_budget = hourly_budget
        self.current_hour_spend = 0.0
        self.hour_start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        self.request_history: List[Dict[str, Any]] = []

    def _reset_if_new_hour(self) -> None:
        current_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        if current_hour > self.hour_start:
            self.hour_start = current_hour
            self.current_hour_spend = 0.0
            self.request_history = []

    def estimate_cost(self, provider_id: str, estimated_tokens: int = 500) -> float:
        canonical_id = canonical_provider_id(provider_id) or provider_id
        try:
            provider = dispatcher.get_provider(canonical_id)
        except KeyError:
            return 0.0
        pricing = _provider_pricing(provider)
        return pricing.estimate(estimated_tokens, estimated_tokens)

    def record_request(
        self,
        provider_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        self._reset_if_new_hour()
        canonical_id = canonical_provider_id(provider_id) or provider_id
        try:
            provider = dispatcher.get_provider(canonical_id)
            pricing = _provider_pricing(provider)
            cost = pricing.estimate(input_tokens, output_tokens)
        except KeyError:
            cost = 0.0
        self.current_hour_spend += cost
        self.request_history.append(
            {
                "provider": canonical_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def budget_remaining(self) -> float:
        self._reset_if_new_hour()
        return max(0.0, self.hourly_budget - self.current_hour_spend)

    def should_use_cheaper_provider(self) -> bool:
        self._reset_if_new_hour()
        return self.current_hour_spend > (self.hourly_budget * 0.7)

    def get_status(self) -> Dict[str, Any]:
        self._reset_if_new_hour()
        return {
            "hourly_budget": self.hourly_budget,
            "current_spend": round(self.current_hour_spend, 4),
            "remaining": round(self.budget_remaining(), 4),
            "hour_start": self.hour_start.isoformat(),
            "request_count": len(self.request_history),
            "should_use_cheaper": self.should_use_cheaper_provider(),
        }


def _last_user_message(messages: Optional[List[Dict[str, Any]]]) -> str:
    """Return the content of the last user-role message, or empty string."""
    if not messages:
        return ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            content = msg.get("content", "")
            return content if isinstance(content, str) else ""
    return ""


class SmartRouter:
    def __init__(
        self,
        strategy: RoutingStrategy = RoutingStrategy.COST_OPTIMIZED,
        hourly_budget: float = 10.0,
    ) -> None:
        self.strategy = strategy
        self.cost_tracker = CostTracker(hourly_budget)

    def _resolve_task_type(
        self,
        task_type: Optional[str],
        messages: Optional[List[Dict[str, Any]]],
        intent: Optional[Any] = None,
    ) -> str:
        """Return an explicit task_type, or derive from intent/messages, or default to CHAT."""
        if task_type:
            return task_type
        # Use intent classification when confidence is high enough — skip PromptClassifier
        if intent is not None:
            try:
                from api.routing.intent_classifier import map_intent_to_task_type  # noqa: PLC0415

                if intent.confidence >= 0.7:
                    mapped = map_intent_to_task_type(intent)
                    if mapped:
                        return mapped
            except Exception:
                pass
        if messages:
            try:
                from api.routing.prompt_classifier import prompt_classifier  # noqa: PLC0415

                return prompt_classifier.classify_messages(messages).value
            except Exception:
                pass
        return TaskType.CHAT.value

    def _model_for_provider(self, provider_id: str) -> str:
        config = dispatcher.get_provider_config(provider_id)
        return (
            str(config.get("default_model", ""))
            or dispatcher.get_provider(provider_id).default_model
        )

    def _build_emergency_selection(self) -> ProviderSelection:
        return ProviderSelection(
            provider_id="mock",
            model="mock-gpt",
            reason="No providers available - using mock",
            fallback_chain=[],
            estimated_cost=0.0,
            expected_latency_ms=0.0,
        )

    def _ordered_candidates(
        self,
        strategy: RoutingStrategy,
        capability: str,
        *,
        messages: Optional[List[Dict[str, Any]]] = None,
        intent: Optional[Any] = None,
        request_id: Optional[str] = None,
    ) -> List[str]:
        candidates = top_providers_for(capability, limit=20)
        if not candidates:
            return []

        provider_costs = {
            provider_id: (
                _provider_pricing(dispatcher.get_provider(provider_id)).input_cost,
                _provider_pricing(dispatcher.get_provider(provider_id)).output_cost,
            )
            for provider_id in candidates
        }

        if strategy == RoutingStrategy.ML_BANDIT:
            try:
                from api.routing.ml_router import bandit_router  # noqa: PLC0415

                routing_request = None
                try:
                    from api.routing.feature_extractor import feature_extractor  # noqa: PLC0415

                    intent_label = getattr(intent, "label", "unknown")
                    intent_conf = getattr(intent, "confidence", 0.0)
                    routing_request = feature_extractor.extract_request(
                        prompt=_last_user_message(messages),
                        task_type=capability,
                        conversation_history=messages or [],
                        intent_label=intent_label.value
                        if hasattr(intent_label, "value")
                        else str(intent_label),
                        intent_confidence=float(intent_conf),
                    )
                except Exception:
                    pass

                return bandit_router.rank(
                    candidates,
                    provider_costs,
                    task_type=capability,
                    request_id=request_id,
                    request=routing_request,
                )
            except Exception:
                pass  # fall through to BALANCED on import/runtime error

        if strategy == RoutingStrategy.COST_OPTIMIZED:
            return cost_router.rank(candidates, provider_costs)
        if strategy == RoutingStrategy.LOCAL_FIRST:
            local_candidates = [
                provider_id
                for provider_id in tier_router.providers_for_tier("local")
                if provider_id in candidates
            ]
            return local_candidates or candidates
        if strategy == RoutingStrategy.LATENCY_OPTIMIZED:
            return latency_router.rank(candidates, provider_costs)
        if strategy == RoutingStrategy.BALANCED:
            return hybrid_router.rank(candidates, provider_costs)

        quality_order = ["anthropic", "openai", "azure_openai", "gemini", "gcp_vllm"]
        prioritized = [provider_id for provider_id in quality_order if provider_id in candidates]
        leftovers = [provider_id for provider_id in candidates if provider_id not in prioritized]
        return prioritized + leftovers

    async def select_provider(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        strategy: Optional[RoutingStrategy] = None,
        preferred_provider: Optional[str] = None,
        task_type: Optional[str] = None,
        request_id: Optional[str] = None,
        intent: Optional[Any] = None,
        user_id: Optional[str] = None,
    ) -> ProviderSelection:
        active_strategy = strategy or self.strategy
        capability = self._resolve_task_type(task_type, messages, intent=intent)

        if preferred_provider:
            canonical_id = canonical_provider_id(preferred_provider) or preferred_provider
            if health_monitor.is_available(canonical_id):
                model = self._model_for_provider(canonical_id)
                return ProviderSelection(
                    provider_id=canonical_id,
                    model=model,
                    reason="Preferred provider selected",
                    fallback_chain=[],
                    estimated_cost=self.cost_tracker.estimate_cost(canonical_id),
                    expected_latency_ms=health_monitor.get_latency(canonical_id),
                )

        ordered = self._ordered_candidates(
            active_strategy,
            capability,
            messages=messages,
            intent=intent,
            request_id=request_id,
        )
        if not ordered:
            return self._build_emergency_selection()

        # Preference re-ranking: float providers the user has high affinity for
        if user_id:
            try:
                from api.services.preference_learner import (
                    preference_learner as _pl,  # noqa: PLC0415
                )

                ordered = await _pl.apply_to_routing(user_id, ordered)
            except Exception:
                pass

        selected = ordered[0]
        return ProviderSelection(
            provider_id=selected,
            model=self._model_for_provider(selected),
            reason=f"Selected via {active_strategy.value}",
            fallback_chain=ordered[1:],
            estimated_cost=self.cost_tracker.estimate_cost(selected),
            expected_latency_ms=health_monitor.get_latency(selected),
        )

    def _record_provider_success(
        self,
        result: Dict[str, Any],
        *,
        provider_id: str,
        req_id: str,
        task_type: str,
        tried: List[str],
    ) -> Dict[str, Any]:
        usage = {}
        result_data = result.get("result")
        if isinstance(result_data, dict):
            usage = result_data.get("usage") or {}
        if not usage and isinstance(result.get("usage"), dict):
            usage = result["usage"]

        latency_ms = float(result.get("latency_ms") or 0.0)
        cost_usd = self.cost_tracker.estimate_cost(provider_id)
        self.cost_tracker.record_request(
            provider_id,
            int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
            int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
        )
        # Note: registry.record_success is NOT called here — the dispatcher's
        # execution layer already calls it. We only add the bandit update.
        try:
            from api.routing.ml_router import bandit_router as _br  # noqa: PLC0415

            _br.record_outcome(
                request_id=req_id,
                task_type=task_type,
                provider_id=provider_id,
                was_selected=True,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                success=True,
            )
        except Exception:
            pass

        result.setdefault(
            "routing",
            {"provider": provider_id, "tried_providers": tried, "request_id": req_id},
        )
        return result

    async def invoke_with_fallback(
        self,
        invoke_fn,
        messages: List[Dict[str, Any]],
        strategy: Optional[RoutingStrategy] = None,
        preferred_provider: Optional[str] = None,
        timeout_ms: int = 30_000,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        import uuid as _uuid  # noqa: PLC0415

        payload = dict(kwargs.get("payload") or {})
        payload.setdefault("messages", messages)

        req_id = str(_uuid.uuid4())
        task_type: str = self._resolve_task_type(kwargs.get("task_type"), messages)
        user_id: Optional[str] = payload.get("user_id") or kwargs.get("user_id")

        selection = await self.select_provider(
            messages=messages,
            strategy=strategy,
            preferred_provider=preferred_provider,
            task_type=task_type,
            request_id=req_id,
            user_id=user_id,
        )

        tried: List[str] = []
        for provider_id in [selection.provider_id, *selection.fallback_chain]:
            tried.append(provider_id)
            model = self._model_for_provider(provider_id)
            try:
                result = await invoke_fn(provider_id, model, payload, timeout_ms)
            except Exception:
                registry.record_failure(provider_id, task_type=task_type)
                continue

            if isinstance(result, dict) and result.get("ok"):
                return self._record_provider_success(
                    result,
                    provider_id=provider_id,
                    req_id=req_id,
                    task_type=task_type,
                    tried=tried,
                )

        return {
            "ok": False,
            "error": "all providers failed",
            "routing": {"provider": "none", "tried_providers": tried, "request_id": req_id},
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "healthy_providers": health_monitor.get_healthy_providers(),
            "available_providers": health_monitor.get_available_providers(),
            "best_providers": health_monitor.get_best_providers(),
            "routing_registry": registry.snapshot(),
            "cost_tracking": self.cost_tracker.get_status(),
        }


smart_router = SmartRouter(strategy=RoutingStrategy.ML_BANDIT)


def get_smart_router() -> SmartRouter:
    return smart_router
