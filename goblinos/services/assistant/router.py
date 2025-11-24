"""
Provider router for Goblin Assistant.
Manages provider selection, health checks, and failover logic.
"""

import time
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from ..providers.base import BaseProvider


class TaskType(Enum):
    """Types of tasks for provider selection."""

    CHAT = "chat"
    CODE = "code"
    HEAVY = "heavy"
    EMBEDDING = "embedding"
    CODE_COMPLETION = "code_completion"


@dataclass
class ProviderHealth:
    """Health status of a provider."""

    name: str
    healthy: bool
    latency_ms: float
    last_check: float
    consecutive_failures: int


class ProviderRouter:
    """Routes requests to appropriate providers based on health, cost, and task type."""

    def __init__(self):
        self.providers: Dict[str, BaseProvider] = {}
        self.health_status: Dict[str, ProviderHealth] = {}
        self.task_weights = {
            TaskType.CODE: ["llama_cpp", "ollama", "openai"],
            TaskType.CHAT: ["llama_cpp", "ollama", "openai", "anthropic"],
            TaskType.HEAVY: ["openai", "anthropic", "llama_cpp"],
            TaskType.EMBEDDING: ["openai", "ollama"],
            TaskType.CODE_COMPLETION: ["llama_cpp", "ollama", "openai"],
        }

    def register_provider(self, name: str, provider: BaseProvider):
        """Register a provider."""
        self.providers[name] = provider
        self.health_status[name] = ProviderHealth(
            name=name, healthy=True, latency_ms=0, last_check=0, consecutive_failures=0
        )

    async def get_provider(
        self, task_type: TaskType, user_id: str = "anonymous"
    ) -> BaseProvider:
        """
        Get the best provider for a task type.
        Uses health checks, cost, and user preferences.
        """
        candidates = self.task_weights.get(task_type, ["openai"])

        # Filter to available providers
        available = [name for name in candidates if name in self.providers]

        if not available:
            raise ValueError(f"No providers available for task type: {task_type}")

        # Check health and select best
        best_provider = None
        best_score = -1

        for name in available:
            health = self.health_status[name]
            provider = self.providers[name]

            # Skip unhealthy providers
            if not health.healthy:
                continue

            # Calculate score based on health, cost, and preferences
            score = self._calculate_provider_score(provider, health, task_type, user_id)

            if score > best_score:
                best_score = score
                best_provider = provider

        if not best_provider:
            raise ValueError(
                f"No healthy providers available for task type: {task_type}"
            )

        return best_provider

    def _calculate_provider_score(
        self,
        provider: BaseProvider,
        health: ProviderHealth,
        task_type: TaskType,
        user_id: str,
    ) -> float:
        """Calculate a score for provider selection."""
        score = 100  # Base score

        # Health bonus
        if health.healthy:
            score += 50
        else:
            return -1  # Unhealthy providers get negative score

        # Latency penalty (lower latency = higher score)
        if health.latency_ms > 0:
            latency_penalty = min(health.latency_ms / 10, 30)  # Max 30 point penalty
            score -= latency_penalty

        # Cost penalty for heavy tasks
        if task_type == TaskType.HEAVY and provider.cost_per_token > 0.00001:
            score -= 20  # Prefer cheaper providers for heavy tasks

        # Local preference bonus
        if "llama" in provider.name.lower() or "ollama" in provider.name.lower():
            score += 10  # Prefer local models for privacy

        return score

    async def health_check_all(self):
        """Run health checks on all providers."""
        tasks = []
        for name, provider in self.providers.items():
            tasks.append(self._check_provider_health(name, provider))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_provider_health(self, name: str, provider: BaseProvider):
        """Check health of a single provider."""
        health = self.health_status[name]
        start_time = time.time()

        try:
            is_healthy = provider.health_check()
            latency_ms = (time.time() - start_time) * 1000

            health.healthy = is_healthy
            health.latency_ms = latency_ms
            health.last_check = time.time()

            if is_healthy:
                health.consecutive_failures = 0
            else:
                health.consecutive_failures += 1

        except Exception as e:
            health.healthy = False
            health.consecutive_failures += 1
            health.latency_ms = (time.time() - start_time) * 1000

    def get_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all providers."""
        return {
            name: {
                "healthy": health.healthy,
                "latency_ms": health.latency_ms,
                "last_check": health.last_check,
                "consecutive_failures": health.consecutive_failures,
            }
            for name, health in self.health_status.items()
        }

    async def health_check_provider(self, provider_name: str) -> bool:
        """Check health of a specific provider."""
        if provider_name not in self.providers:
            return False

        provider = self.providers[provider_name]
        await self._check_provider_health(provider_name, provider)
        return self.health_status[provider_name].healthy

    async def estimate_cost(self, task_type: TaskType, estimated_tokens: int) -> float:
        """Estimate cost for a task."""
        try:
            provider = await self.get_provider(task_type)
            return provider.estimate_cost(estimated_tokens)
        except Exception:
            return 0.0  # Return 0 if estimation fails
