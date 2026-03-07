"""
Smart Router - Intelligent AI Provider Routing

Provides intelligent routing with:
- Health-aware provider selection
- Cost optimization
- Capability-based routing
- Fallback chains with automatic failover
- Circuit breaker integration
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
import os

from .provider_health import health_monitor

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of AI tasks for capability routing."""

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
    """Available routing strategies."""

    COST_OPTIMIZED = "cost_optimized"
    QUALITY_FIRST = "quality_first"
    LATENCY_OPTIMIZED = "latency_optimized"
    BALANCED = "balanced"
    LOCAL_FIRST = "local_first"


@dataclass
class ProviderCost:
    """Cost information for a provider (per 1K tokens)."""

    input_cost: float  # USD per 1K input tokens
    output_cost: float  # USD per 1K output tokens

    def estimate(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for request."""
        return (
            input_tokens / 1000 * self.input_cost
            + output_tokens / 1000 * self.output_cost
        )


@dataclass
class ProviderSelection:
    """Result of provider selection."""

    provider_id: str
    model: str
    reason: str
    fallback_chain: List[str]
    estimated_cost: float
    expected_latency_ms: float


# Provider cost mapping (USD per 1K tokens: input/output)
PROVIDER_COSTS: Dict[str, ProviderCost] = {
    # Very cheap cloud
    "groq": ProviderCost(0.05, 0.10),
    "siliconeflow": ProviderCost(0.01, 0.03),
    # Budget cloud
    "deepseek": ProviderCost(0.14, 0.28),
    # Standard cloud
    "openai": ProviderCost(0.50, 1.50),  # GPT-4o-mini default
    "azure": ProviderCost(0.15, 0.60),  # Azure OpenAI gpt-4o-mini
    "google": ProviderCost(0.35, 1.05),  # Gemini Pro
    "gemini": ProviderCost(0.35, 1.05),  # Gemini (alias)
    # Premium cloud
    "anthropic": ProviderCost(3.00, 15.00),  # Claude 3 Sonnet
    # Additional cloud
    "vertex_ai": ProviderCost(0.35, 1.05),  # Vertex AI Gemini
    "aliyun": ProviderCost(0.02, 0.06),  # DashScope Qwen
}

# Provider capabilities
PROVIDER_CAPABILITIES: Dict[str, List[str]] = {
    "groq": ["chat", "code", "reasoning"],
    "openai": ["chat", "code", "reasoning", "vision", "embedding", "image"],
    "anthropic": ["chat", "code", "reasoning", "vision"],
    "deepseek": ["chat", "code", "reasoning"],
    "siliconeflow": ["chat", "code"],
    "azure": ["chat", "code", "reasoning"],
    "aliyun": ["chat", "code"],
    "google": ["chat", "code", "reasoning", "vision"],
    "gemini": ["chat", "code", "reasoning", "vision"],
    "vertex_ai": ["chat", "code", "reasoning", "vision"],
}

# Default models per provider
DEFAULT_MODELS: Dict[str, str] = {
    "groq": "llama-3.1-8b-instant",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-20241022",
    "deepseek": "deepseek-chat",
    "siliconeflow": "Qwen/Qwen2.5-7B-Instruct",
    "azure": "gpt-4o-mini",
    "google": "gemini-pro",
    "gemini": "gemini-2.0-flash",
    "vertex_ai": "gemini-2.0-flash",
    "aliyun": "qwen-turbo",
}

# Environment variables required for each provider
PROVIDER_ENV_VARS: Dict[str, str] = {
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "siliconeflow": "SILICONEFLOW_API_KEY",
    "azure": "AZURE_API_KEY",
    "google": "GOOGLE_AI_API_KEY",
    "gemini": "GOOGLE_AI_API_KEY",
    "vertex_ai": "GCP_ACCESS_TOKEN",
    "aliyun": "DASHSCOPE_API_KEY",
}

# Fallback chains for different strategies
FALLBACK_CHAINS: Dict[str, List[str]] = {
    "cost_optimized": [
        "groq",
        "siliconeflow",
        "aliyun",
        "azure",
        "deepseek",
        "gemini",
        "vertex_ai",
        "openai",
        "anthropic",
    ],
    "quality_first": [
        "azure",
        "groq",
        "deepseek",
        "openai",
        "anthropic",
        "gemini",
    ],
    "latency_optimized": [
        "groq",
        "azure",
        "deepseek",
        "openai",
        "anthropic",
    ],
    "local_first": [
        "groq",
        "azure",
        "openai",
    ],
    "balanced": [
        "groq",
        "siliconeflow",
        "aliyun",
        "azure",
        "deepseek",
        "openai",
        "anthropic",
        "gemini",
        "vertex_ai",
    ],
    # Task-specific chains
    "code_generation": [
        "deepseek",
        "groq",
        "azure",
        "openai",
        "anthropic",
    ],
    "reasoning": [
        "groq",
        "azure",
        "deepseek",
        "openai",
        "anthropic",
    ],
}


class CostTracker:
    """
    Track and optimize AI provider costs.

    Maintains hourly budget tracking and provides
    cost-aware routing recommendations.
    """

    def __init__(self, hourly_budget: float = 10.0):
        """
        Initialize cost tracker.

        Args:
            hourly_budget: Maximum USD to spend per hour
        """
        self.hourly_budget = hourly_budget
        self.current_hour_spend = 0.0
        self.hour_start = datetime.now(timezone.utc).replace(
            minute=0, second=0, microsecond=0
        )
        self.request_history: List[Dict[str, Any]] = []

    def _reset_if_new_hour(self):
        """Reset tracking if we're in a new hour."""
        current_hour = datetime.now(timezone.utc).replace(
            minute=0, second=0, microsecond=0
        )
        if current_hour > self.hour_start:
            self.hour_start = current_hour
            self.current_hour_spend = 0.0
            self.request_history = []

    def record_request(
        self,
        provider_id: str,
        input_tokens: int,
        output_tokens: int,
    ):
        """Record a completed request and its cost."""
        self._reset_if_new_hour()

        if provider_id in PROVIDER_COSTS:
            cost = PROVIDER_COSTS[provider_id].estimate(input_tokens, output_tokens)
        else:
            cost = 0.0

        self.current_hour_spend += cost
        self.request_history.append(
            {
                "provider": provider_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        logger.debug(
            "Recorded cost: $%.4f for %s (hourly total: $%.2f)",
            cost,
            provider_id,
            self.current_hour_spend,
        )

    def estimate_cost(
        self,
        provider_id: str,
        estimated_tokens: int = 500,
    ) -> float:
        """Estimate cost for a request."""
        if provider_id not in PROVIDER_COSTS:
            return 0.0
        # Assume 1:1 input:output ratio for estimation
        return PROVIDER_COSTS[provider_id].estimate(estimated_tokens, estimated_tokens)

    def budget_remaining(self) -> float:
        """Get remaining budget for current hour."""
        self._reset_if_new_hour()
        return max(0, self.hourly_budget - self.current_hour_spend)

    def should_use_cheaper_provider(self) -> bool:
        """Check if we should prefer cheaper providers."""
        self._reset_if_new_hour()
        # Use cheaper providers if we've spent >70% of budget
        return self.current_hour_spend > (self.hourly_budget * 0.7)

    def get_affordable_providers(
        self,
        providers: List[str],
        max_cost: Optional[float] = None,
    ) -> List[str]:
        """Filter providers by affordability."""
        if max_cost is None:
            max_cost = (
                self.budget_remaining() * 0.1
            )  # 10% of remaining budget per request

        return [
            p
            for p in providers
            if self.estimate_cost(p) <= max_cost or self.estimate_cost(p) == 0
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get current cost tracking status."""
        self._reset_if_new_hour()
        return {
            "hourly_budget": self.hourly_budget,
            "current_spend": round(self.current_hour_spend, 4),
            "remaining": round(self.budget_remaining(), 4),
            "hour_start": self.hour_start.isoformat(),
            "request_count": len(self.request_history),
            "should_use_cheaper": self.should_use_cheaper_provider(),
        }


class SmartRouter:
    """
    Intelligent AI provider routing.

    Features:
    - Health-aware selection (skips unhealthy providers)
    - Cost optimization with budget tracking
    - Capability-based routing
    - Automatic fallback chains
    - Circuit breaker integration
    """

    def __init__(
        self,
        strategy: RoutingStrategy = RoutingStrategy.COST_OPTIMIZED,
        hourly_budget: float = 10.0,
    ):
        """
        Initialize smart router.

        Args:
            strategy: Default routing strategy
            hourly_budget: Maximum USD to spend per hour
        """
        self.default_strategy = strategy
        self.cost_tracker = CostTracker(hourly_budget)
        self._circuit_breakers: Dict[str, Any] = {}  # Will be populated from ops_router

    def set_circuit_breakers(self, breakers: Dict[str, Any]):
        """Set reference to circuit breakers."""
        self._circuit_breakers = breakers

    def _is_circuit_open(self, provider_id: str) -> bool:
        """Check if circuit breaker is open for provider."""
        if provider_id not in self._circuit_breakers:
            return False
        breaker = self._circuit_breakers[provider_id]
        return hasattr(breaker, "state") and breaker.state == "OPEN"

    def _detect_task_type(self, messages: List[Dict[str, str]]) -> TaskType:
        """
        Detect task type from message content.

        Uses simple keyword matching for task classification.
        """
        if not messages:
            return TaskType.CHAT

        # Get last user message
        last_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "").lower()
                break

        # Code generation keywords
        code_keywords = [
            "write code",
            "code for",
            "implement",
            "function",
            "class",
            "python",
            "javascript",
            "typescript",
            "java",
            "rust",
            "algorithm",
            "script",
            "program",
            "debug",
            "fix this code",
        ]

        # Reasoning keywords
        reasoning_keywords = [
            "why",
            "explain",
            "analyze",
            "compare",
            "reason",
            "think through",
            "step by step",
            "evaluate",
            "assess",
        ]

        # Summary keywords
        summary_keywords = [
            "summarize",
            "summary",
            "tldr",
            "brief",
            "overview",
            "key points",
            "main ideas",
        ]

        # Check for matches
        for keyword in code_keywords:
            if keyword in last_message:
                return TaskType.CODE_GENERATION

        for keyword in reasoning_keywords:
            if keyword in last_message:
                return TaskType.REASONING

        for keyword in summary_keywords:
            if keyword in last_message:
                return TaskType.SUMMARIZATION

        return TaskType.CHAT

    def _get_capable_providers(self, task_type: TaskType) -> List[str]:
        """Get providers capable of handling task type."""
        capability = task_type.value
        return [
            pid
            for pid, caps in PROVIDER_CAPABILITIES.items()
            if capability in caps or "chat" in caps  # Chat is universal
        ]

    def _get_fallback_chain(
        self,
        strategy: RoutingStrategy,
        task_type: TaskType,
    ) -> List[str]:
        """Get fallback chain for strategy and task type."""
        # Check for task-specific chain
        if (
            task_type == TaskType.CODE_GENERATION
            and "code_generation" in FALLBACK_CHAINS
        ):
            return FALLBACK_CHAINS["code_generation"]
        if task_type == TaskType.REASONING and "reasoning" in FALLBACK_CHAINS:
            return FALLBACK_CHAINS["reasoning"]

        # Use strategy-based chain
        return FALLBACK_CHAINS.get(strategy.value, FALLBACK_CHAINS["balanced"])

    @staticmethod
    def _provider_has_capabilities(
        provider_id: str, required_capabilities: Optional[List[str]]
    ) -> bool:
        if not required_capabilities:
            return True
        provider_caps = PROVIDER_CAPABILITIES.get(provider_id, [])
        return all(cap in provider_caps for cap in required_capabilities)

    def _provider_is_eligible(
        self,
        provider_id: str,
        exclude_providers: List[str],
        required_capabilities: Optional[List[str]],
    ) -> tuple[bool, Optional[str]]:
        if provider_id in exclude_providers:
            return False, None

        if not health_monitor.is_available(provider_id):
            return False, f"Skipped {provider_id}: unhealthy"

        if self._is_circuit_open(provider_id):
            return False, f"Skipped {provider_id}: circuit open"

        if not self._provider_has_capabilities(provider_id, required_capabilities):
            return False, f"Skipped {provider_id}: missing capabilities"

        # Check that the required API key env var is set
        env_var = PROVIDER_ENV_VARS.get(provider_id)
        if env_var and not os.getenv(env_var, "").strip():
            return False, f"Skipped {provider_id}: {env_var} not configured"

        return True, None

    def _should_skip_for_budget(
        self, provider_id: str, filtered_chain: List[str]
    ) -> bool:
        if not self.cost_tracker.should_use_cheaper_provider():
            return False
        cost = self.cost_tracker.estimate_cost(provider_id)
        return cost > 0.01 and len(filtered_chain) > 0

    def _filter_fallback_chain(
        self,
        fallback_chain: List[str],
        exclude_providers: List[str],
        required_capabilities: Optional[List[str]],
    ) -> tuple[List[str], List[str]]:
        filtered_chain: List[str] = []
        selection_reason: List[str] = []

        for provider_id in fallback_chain:
            is_eligible, reason = self._provider_is_eligible(
                provider_id, exclude_providers, required_capabilities
            )
            if not is_eligible:
                if reason:
                    selection_reason.append(reason)
                continue

            if self._should_skip_for_budget(provider_id, filtered_chain):
                selection_reason.append(f"Skipped {provider_id}: over budget")
                continue

            filtered_chain.append(provider_id)

        return filtered_chain, selection_reason

    def _build_emergency_selection(self) -> ProviderSelection:
        return ProviderSelection(
            provider_id="mock",
            model="mock-gpt",
            reason="No providers available - using mock",
            fallback_chain=[],
            estimated_cost=0,
            expected_latency_ms=100,
        )

    def _preferred_provider_selection(
        self, preferred_provider: Optional[str]
    ) -> Optional[ProviderSelection]:
        if not preferred_provider:
            return None

        if not health_monitor.is_available(preferred_provider):
            return None

        if self._is_circuit_open(preferred_provider):
            return None

        return ProviderSelection(
            provider_id=preferred_provider,
            model=DEFAULT_MODELS.get(preferred_provider, "default"),
            reason="User-preferred provider",
            fallback_chain=[],
            estimated_cost=self.cost_tracker.estimate_cost(preferred_provider),
            expected_latency_ms=health_monitor.get_latency(preferred_provider),
        )

    def select_provider(
        self,
        messages: List[Dict[str, str]],
        strategy: Optional[RoutingStrategy] = None,
        required_capabilities: Optional[List[str]] = None,
        preferred_provider: Optional[str] = None,
        exclude_providers: Optional[List[str]] = None,
    ) -> ProviderSelection:
        """
        Select the best provider for a request.

        Selection process:
        1. Detect task type from messages
        2. Get fallback chain for strategy
        3. Filter by health status
        4. Filter by circuit breaker state
        5. Filter by capabilities
        6. Filter by cost (if budget limited)
        7. Return first available provider

        Args:
            messages: Conversation messages
            strategy: Routing strategy (defaults to instance default)
            required_capabilities: Capabilities required for task
            preferred_provider: Override to use specific provider
            exclude_providers: Providers to skip

        Returns:
            ProviderSelection with provider, model, and reasoning
        """
        strategy = strategy or self.default_strategy
        exclude_providers = exclude_providers or []

        preferred_selection = self._preferred_provider_selection(preferred_provider)
        if preferred_selection is not None:
            return preferred_selection

        # Detect task type
        task_type = self._detect_task_type(messages)

        # Get base fallback chain
        fallback_chain = self._get_fallback_chain(strategy, task_type)

        filtered_chain: List[str]
        filtered_chain, _ = self._filter_fallback_chain(
            fallback_chain, exclude_providers, required_capabilities
        )

        # Select first available
        if not filtered_chain:
            return self._build_emergency_selection()

        selected = filtered_chain[0]
        remaining_chain = filtered_chain[1:]

        return ProviderSelection(
            provider_id=selected,
            model=DEFAULT_MODELS.get(selected, "default"),
            reason=f"Selected via {strategy.value} strategy for {task_type.value}",
            fallback_chain=remaining_chain,
            estimated_cost=self.cost_tracker.estimate_cost(selected),
            expected_latency_ms=health_monitor.get_latency(selected),
        )

    async def invoke_with_fallback(
        self,
        invoke_fn,  # Callable[[str, str, Dict, int], Awaitable[Dict]]
        messages: List[Dict[str, str]],
        timeout_ms: int = 30000,
        strategy: Optional[RoutingStrategy] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Invoke provider with automatic fallback on failure.

        Args:
            invoke_fn: Function to invoke provider (provider_id, model, payload, timeout)
            messages: Conversation messages
            timeout_ms: Request timeout
            strategy: Routing strategy
            **kwargs: Additional arguments for provider selection

        Returns:
            Provider response or error
        """
        selection = self.select_provider(messages, strategy, **kwargs)
        tried_providers = []

        chain = [selection.provider_id] + selection.fallback_chain

        for provider_id in chain:
            model = DEFAULT_MODELS.get(provider_id, "default")
            tried_providers.append(provider_id)

            logger.info("Trying provider: %s (%s)", provider_id, model)

            try:
                result = await invoke_fn(
                    provider_id,
                    model,
                    {"messages": messages},
                    timeout_ms,
                )

                if result.get("ok"):
                    # Record success
                    self.cost_tracker.record_request(
                        provider_id,
                        result.get("usage", {}).get("prompt_tokens", 100),
                        result.get("usage", {}).get("completion_tokens", 100),
                    )

                    # Add routing metadata
                    result["routing"] = {
                        "provider": provider_id,
                        "model": model,
                        "strategy": strategy.value
                        if strategy
                        else self.default_strategy.value,
                        "tried_providers": tried_providers,
                        "fallback_used": len(tried_providers) > 1,
                    }

                    return result
                else:
                    logger.warning(
                        "Provider %s returned error: %s",
                        provider_id,
                        result.get("error"),
                    )

            except (
                RuntimeError,
                ValueError,
                TypeError,
            ) as e:
                logger.error("Provider %s exception: %s", provider_id, e)
                continue

        return {
            "ok": False,
            "error": "all-providers-failed",
            "tried_providers": tried_providers,
        }

    def get_status(self) -> Dict[str, Any]:
        """Get router status."""
        return {
            "default_strategy": self.default_strategy.value,
            "cost_tracking": self.cost_tracker.get_status(),
            "healthy_providers": health_monitor.get_healthy_providers(),
            "available_providers": health_monitor.get_available_providers(),
            "best_providers": health_monitor.get_best_providers(),
        }


# Global smart router instance
smart_router = SmartRouter(
    strategy=RoutingStrategy.COST_OPTIMIZED,
    hourly_budget=10.0,
)


def get_smart_router() -> SmartRouter:
    """Get the global smart router instance."""
    return smart_router
