"""
MCP Provider System

This module defines the provider interface and implementations for various AI models
including OpenAI, Anthropic, and local models.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import asyncio
import time
import json
import os
from dataclasses import dataclass
from enum import Enum


class ProviderType(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    REPLICATE = "replicate"


class CircuitBreakerState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, requests rejected
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class ProviderResponse:
    """Response from a provider call."""

    content: str
    tokens_used: int
    cost_usd: float
    metadata: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


@dataclass
class ProviderConfig:
    """Configuration for a provider."""

    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 30
    retry_attempts: int = 3
    rate_limit_per_minute: int = 60


class CircuitBreaker:
    """Circuit breaker for provider reliability."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Exception = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class Provider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.circuit_breaker = CircuitBreaker()
        self.last_request_time = 0
        self.request_count = 0

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        """Generate response from the provider."""
        pass

    @abstractmethod
    def estimate_cost(self, prompt: str, max_tokens: int = 1000) -> float:
        """Estimate cost for a request."""
        pass

    def should_rate_limit(self) -> bool:
        """Check if we should rate limit."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < 60 / self.config.rate_limit_per_minute:
            return True

        return False

    def record_request(self):
        """Record a request for rate limiting."""
        self.last_request_time = time.time()
        self.request_count += 1


class OpenAIProvider(Provider):
    """OpenAI provider implementation."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        try:
            from openai import AsyncOpenAI

            self.client = AsyncOpenAI(api_key=config.api_key)
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai"
            )

    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        """Generate response using OpenAI."""
        if self.should_rate_limit():
            await asyncio.sleep(1)  # Simple rate limiting

        try:
            self.record_request()

            response = await self.client.chat.completions.create(
                model=self.config.model_name or "gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature),
                timeout=self.config.timeout,
            )

            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            cost_usd = self.estimate_cost(prompt, tokens_used)

            return ProviderResponse(
                content=content,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                metadata={
                    "model": response.model,
                    "finish_reason": response.choices[0].finish_reason,
                },
                success=True,
            )

        except Exception as e:
            return ProviderResponse(
                content="",
                tokens_used=0,
                cost_usd=0.0,
                metadata={},
                success=False,
                error_message=str(e),
            )

    def estimate_cost(self, prompt: str, max_tokens: int = 1000) -> float:
        """Estimate OpenAI cost."""
        # Rough estimates per 1K tokens
        costs = {
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        }

        model_costs = costs.get(self.config.model_name, costs["gpt-3.5-turbo"])
        input_tokens = len(prompt.split()) * 1.3  # Rough estimate
        total_cost = (input_tokens / 1000 * model_costs["input"]) + (
            max_tokens / 1000 * model_costs["output"]
        )

        return total_cost


class AnthropicProvider(Provider):
    """Anthropic provider implementation."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        try:
            import anthropic

            self.client = anthropic.AsyncAnthropic(api_key=config.api_key)
        except ImportError:
            raise ImportError(
                "Anthropic package not installed. Install with: pip install anthropic"
            )

    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        """Generate response using Anthropic."""
        if self.should_rate_limit():
            await asyncio.sleep(1)

        try:
            self.record_request()

            response = await self.client.messages.create(
                model=self.config.model_name or "claude-3-sonnet-20240229",
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature),
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            cost_usd = self.estimate_cost(prompt, tokens_used)

            return ProviderResponse(
                content=content,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                metadata={"model": response.model, "stop_reason": response.stop_reason},
                success=True,
            )

        except Exception as e:
            return ProviderResponse(
                content="",
                tokens_used=0,
                cost_usd=0.0,
                metadata={},
                success=False,
                error_message=str(e),
            )

    def estimate_cost(self, prompt: str, max_tokens: int = 1000) -> float:
        """Estimate Anthropic cost."""
        # Rough estimates per 1K tokens
        costs = {
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        }

        model_costs = costs.get(self.config.model_name, costs["claude-3-sonnet"])
        input_tokens = len(prompt.split()) * 1.3
        total_cost = (input_tokens / 1000 * model_costs["input"]) + (
            max_tokens / 1000 * model_costs["output"]
        )

        return total_cost


class LocalProvider(Provider):
    """Local model provider (e.g., Ollama, LM Studio)."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        try:
            import httpx

            self.http_client = httpx.AsyncClient(timeout=config.timeout)
        except ImportError:
            raise ImportError(
                "httpx package not installed. Install with: pip install httpx"
            )

    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        """Generate response using local model."""
        if self.should_rate_limit():
            await asyncio.sleep(1)

        try:
            self.record_request()

            # Ollama-style API
            payload = {
                "model": self.config.model_name or "llama2",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", self.config.temperature),
                    "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                },
            }

            response = await self.http_client.post(
                f"{self.config.base_url or 'http://localhost:11434'}/api/generate",
                json=payload,
            )
            response.raise_for_status()

            data = response.json()
            content = data.get("response", "")
            tokens_used = len(content.split()) + len(prompt.split())  # Rough estimate
            cost_usd = 0.0  # Local models are free

            return ProviderResponse(
                content=content,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                metadata={
                    "model": data.get("model"),
                    "total_duration": data.get("total_duration"),
                    "load_duration": data.get("load_duration"),
                },
                success=True,
            )

        except Exception as e:
            return ProviderResponse(
                content="",
                tokens_used=0,
                cost_usd=0.0,
                metadata={},
                success=False,
                error_message=str(e),
            )

    def estimate_cost(self, prompt: str, max_tokens: int = 1000) -> float:
        """Local models have no cost."""
        return 0.0


class ProviderRegistry:
    """Registry for managing providers."""

    def __init__(self):
        self.providers: Dict[str, Provider] = {}
        self.provider_configs: Dict[str, ProviderConfig] = {}

    def register_provider(
        self, name: str, provider_type: ProviderType, config: ProviderConfig
    ):
        """Register a provider."""
        self.provider_configs[name] = config

        if provider_type == ProviderType.OPENAI:
            self.providers[name] = OpenAIProvider(config)
        elif provider_type == ProviderType.ANTHROPIC:
            self.providers[name] = AnthropicProvider(config)
        elif provider_type == ProviderType.LOCAL:
            self.providers[name] = LocalProvider(config)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

    def get_provider(self, name: str) -> Optional[Provider]:
        """Get a provider by name."""
        return self.providers.get(name)

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return list(self.providers.keys())

    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all providers."""
        status = {}
        for name, provider in self.providers.items():
            status[name] = {
                "circuit_breaker_state": provider.circuit_breaker.state.value,
                "request_count": provider.request_count,
                "last_request_time": provider.last_request_time,
            }
        return status


# Global provider registry
provider_registry = ProviderRegistry()


class ProviderManager:
    """Advanced provider manager with intelligent routing and circuit breaker awareness."""

    def __init__(self):
        self.registry = provider_registry

    def list_providers(self) -> List[str]:
        """List all available providers."""
        return self.registry.get_available_providers()

    def get_provider_status(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a specific provider."""
        provider = self.registry.get_provider(provider_name)
        if not provider:
            return None

        return {
            "name": provider_name,
            "circuit_breaker_state": provider.circuit_breaker.state.value,
            "failure_count": provider.circuit_breaker.failure_count,
            "last_failure_time": provider.circuit_breaker.last_failure_time,
            "request_count": provider.request_count,
            "last_request_time": provider.last_request_time,
            "is_healthy": self._is_provider_healthy(provider_name),
        }

    def get_provider(self, name: str) -> Optional[Provider]:
        """Get a provider by name."""
        return self.registry.get_provider(name)

    def _is_provider_healthy(self, provider_name: str) -> bool:
        """Check if a provider is healthy (circuit breaker not open)."""
        provider = self.registry.get_provider(provider_name)
        if not provider:
            return False
        return provider.circuit_breaker.state != CircuitBreakerState.OPEN

    def route_request(self, request_data: Dict[str, Any]) -> Optional[str]:
        """
        Intelligent provider routing based on request characteristics and provider health.

        Routing logic:
        1. If provider_hint specified and healthy, use it
        2. Prefer local models if prefer_local=True
        3. Route based on task type and priority
        4. Consider cost and performance
        5. Avoid providers with open circuit breakers
        """
        available_providers = [
            p for p in self.list_providers() if self._is_provider_healthy(p)
        ]

        if not available_providers:
            return None

        # 1. Check for explicit provider hint
        provider_hint = request_data.get("provider_hint")
        if provider_hint and provider_hint in available_providers:
            return provider_hint

        # 2. Prefer local models for privacy/cost
        if request_data.get("prefer_local", False):
            local_providers = [p for p in available_providers if p.startswith("local")]
            if local_providers:
                return self._select_best_provider(local_providers, request_data)

        # 3. Route based on task type
        task_type = request_data.get("task_type", "chat")
        priority = request_data.get("priority", 50)

        if task_type == "code" and priority > 70:
            # High priority code tasks need best models
            code_providers = ["openai-gpt4", "anthropic-opus", "anthropic-sonnet"]
            healthy_code_providers = [
                p for p in code_providers if p in available_providers
            ]
            if healthy_code_providers:
                return healthy_code_providers[0]  # Best available

        elif task_type == "workflow":
            # Workflows need reliable models
            workflow_providers = ["anthropic-sonnet", "openai-gpt4", "openai-gpt35"]
            healthy_workflow_providers = [
                p for p in workflow_providers if p in available_providers
            ]
            if healthy_workflow_providers:
                return healthy_workflow_providers[0]

        # 4. Default routing by cost/performance balance
        return self._select_best_provider(available_providers, request_data)

    def _select_best_provider(
        self, candidates: List[str], request_data: Dict[str, Any]
    ) -> str:
        """Select the best provider from candidates based on various factors."""
        if len(candidates) == 1:
            return candidates[0]

        # Score providers based on multiple factors
        scored_providers = []
        for provider_name in candidates:
            score = self._calculate_provider_score(provider_name, request_data)
            scored_providers.append((provider_name, score))

        # Sort by score (higher is better) and return best
        scored_providers.sort(key=lambda x: x[1], reverse=True)
        return scored_providers[0][0]

    def _calculate_provider_score(
        self, provider_name: str, request_data: Dict[str, Any]
    ) -> float:
        """Calculate a score for provider selection (higher is better)."""
        base_score = 50.0

        # Cost factor (prefer cheaper)
        cost_estimate = self._estimate_provider_cost(provider_name, request_data)
        if cost_estimate == 0:
            base_score += 30  # Free local models get big bonus
        elif cost_estimate < 0.01:
            base_score += 20
        elif cost_estimate < 0.05:
            base_score += 10

        # Reliability factor (avoid recently failed providers)
        provider = self.registry.get_provider(provider_name)
        if provider and provider.circuit_breaker.failure_count == 0:
            base_score += 15  # Perfect reliability bonus

        # Performance factor (prefer faster providers)
        if "gpt35" in provider_name:
            base_score += 10  # GPT-3.5 is fast
        elif "local" in provider_name:
            base_score += 5  # Local models can be fast

        # Capability factor (prefer more capable models for complex tasks)
        priority = request_data.get("priority", 50)
        if priority > 80:
            if "gpt4" in provider_name or "opus" in provider_name:
                base_score += 20  # Best models for high priority

        return base_score

    def _estimate_provider_cost(
        self, provider_name: str, request_data: Dict[str, Any]
    ) -> float:
        """Estimate cost for a provider based on request characteristics."""
        provider = self.registry.get_provider(provider_name)
        if not provider:
            return 999.0

        prompt = request_data.get("prompt", "")
        return provider.estimate_cost(prompt, 1000)  # Rough estimate

    def reset_circuit_breaker(self, provider_name: str) -> bool:
        """Manually reset a provider's circuit breaker."""
        provider = self.registry.get_provider(provider_name)
        if provider:
            provider.circuit_breaker.failure_count = 0
            provider.circuit_breaker.state = CircuitBreakerState.CLOSED
            provider.circuit_breaker.last_failure_time = None
            return True
        return False


# Global provider manager instance
provider_manager = ProviderManager()


def initialize_providers():
    """Initialize providers from environment variables."""

    # OpenAI
    if os.getenv("OPENAI_API_KEY"):
        provider_registry.register_provider(
            "openai-gpt4",
            ProviderType.OPENAI,
            ProviderConfig(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name="gpt-4",
                rate_limit_per_minute=50,
            ),
        )

        provider_registry.register_provider(
            "openai-gpt35",
            ProviderType.OPENAI,
            ProviderConfig(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name="gpt-3.5-turbo",
                rate_limit_per_minute=3500,
            ),
        )

    # Anthropic
    if os.getenv("ANTHROPIC_API_KEY"):
        provider_registry.register_provider(
            "anthropic-opus",
            ProviderType.ANTHROPIC,
            ProviderConfig(
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model_name="claude-3-opus-20240229",
                rate_limit_per_minute=50,
            ),
        )

        provider_registry.register_provider(
            "anthropic-sonnet",
            ProviderType.ANTHROPIC,
            ProviderConfig(
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model_name="claude-3-sonnet-20240229",
                rate_limit_per_minute=50,
            ),
        )

    # Local (Ollama)
    provider_registry.register_provider(
        "local-llama",
        ProviderType.LOCAL,
        ProviderConfig(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model_name="llama2",
            rate_limit_per_minute=60,
        ),
    )


# Initialize providers on import
initialize_providers()

# Global provider manager instance
provider_manager = ProviderManager()
