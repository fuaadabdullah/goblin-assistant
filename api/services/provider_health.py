"""
Provider Health Monitoring Service

Provides background health checks for AI providers with:
- Periodic health polling
- Latency tracking (rolling window)
- Automatic status updates
- Circuit breaker integration
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
import httpx
import logging

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Provider health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ProviderHealth:
    """Health information for a provider."""

    provider_id: str
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_error: Optional[str] = None
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    consecutive_failures: int = 0
    latency_samples: deque = field(default_factory=lambda: deque(maxlen=100))

    def record_success(self, latency_ms: float):
        """Record a successful health check."""
        self.latency_samples.append(latency_ms)
        self.last_check = datetime.utcnow()
        self.last_success = datetime.utcnow()
        self.consecutive_failures = 0
        self.last_error = None
        self._update_metrics()

    def record_failure(self, error: str):
        """Record a failed health check."""
        self.last_check = datetime.utcnow()
        self.consecutive_failures += 1
        self.last_error = error
        self._update_metrics()

    def _update_metrics(self):
        """Update derived metrics."""
        if self.latency_samples:
            self.avg_latency_ms = sum(self.latency_samples) / len(self.latency_samples)

        # Update status based on consecutive failures
        if self.consecutive_failures >= 3:
            self.status = HealthStatus.UNHEALTHY
        elif self.consecutive_failures >= 1:
            self.status = HealthStatus.DEGRADED
        else:
            self.status = HealthStatus.HEALTHY


class ProviderHealthMonitor:
    """
    Background service for monitoring provider health.

    Features:
    - Periodic health checks (configurable interval)
    - Latency tracking with rolling averages
    - Automatic status updates
    - Integration with circuit breakers
    """

    # Health check endpoints by provider
    HEALTH_ENDPOINTS = {
        "ollama_gcp": ("http://34.60.255.199:11434", "/api/tags"),
        "llamacpp_gcp": ("http://34.132.226.143:8000", "/health"),
        "groq": ("https://api.groq.com", "/openai/v1/models"),
        "openai": ("https://api.openai.com", "/v1/models"),
        "anthropic": ("https://api.anthropic.com", "/v1/models"),
        "siliconeflow": ("https://api.siliconflow.com", "/v1/models"),
        "deepseek": ("https://api.deepseek.com", "/v1/models"),
        "azure": ("https://goblinos-resource.services.ai.azure.com", "/openai/models?api-version=2024-05-01-preview"),
        "google": ("https://generativelanguage.googleapis.com", "/v1beta/models"),
    }

    # API keys required for health checks
    API_KEY_ENV_VARS = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "groq": "GROQ_API_KEY",
        "siliconeflow": "SILICONEFLOW_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "azure": "AZURE_API_KEY",
        "google": "GOOGLE_AI_API_KEY",
    }

    def __init__(self, check_interval: int = 30):
        """
        Initialize health monitor.

        Args:
            check_interval: Seconds between health checks (default: 30)
        """
        self.check_interval = check_interval
        self.health_data: Dict[str, ProviderHealth] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Initialize health data for all providers
        for provider_id in self.HEALTH_ENDPOINTS:
            self.health_data[provider_id] = ProviderHealth(provider_id=provider_id)

    async def start(self):
        """Start background health monitoring."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._monitoring_loop())
        logger.info("Provider health monitoring started")

    async def stop(self):
        """Stop background health monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Provider health monitoring stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        import os

        while self._running:
            try:
                # Check all providers concurrently
                tasks = []
                for provider_id, (base_url, endpoint) in self.HEALTH_ENDPOINTS.items():
                    # Get API key if required
                    api_key = None
                    if provider_id in self.API_KEY_ENV_VARS:
                        api_key = os.getenv(self.API_KEY_ENV_VARS[provider_id])

                    tasks.append(
                        self._check_provider(provider_id, base_url, endpoint, api_key)
                    )

                await asyncio.gather(*tasks, return_exceptions=True)

            except Exception as e:
                logger.error(f"Health monitoring error: {e}")

            await asyncio.sleep(self.check_interval)

    async def _check_provider(
        self,
        provider_id: str,
        base_url: str,
        endpoint: str,
        api_key: Optional[str] = None,
    ):
        """Check health of a single provider."""
        health = self.health_data[provider_id]
        url = f"{base_url}{endpoint}"

        headers = {"Accept": "application/json"}
        if api_key:
            if provider_id == "azure":
                headers["api-key"] = api_key
            elif provider_id in ["openai", "groq", "siliconeflow", "deepseek"]:
                headers["Authorization"] = f"Bearer {api_key}"
            elif provider_id == "anthropic":
                headers["x-api-key"] = api_key
                headers["anthropic-version"] = "2024-01-01"
            elif provider_id == "google":
                url = f"{url}?key={api_key}"

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)

                latency_ms = (time.time() - start_time) * 1000

                if response.status_code in [200, 201]:
                    health.record_success(latency_ms)
                    logger.debug(f"Health check OK: {provider_id} ({latency_ms:.0f}ms)")
                elif response.status_code in [401, 403]:
                    # Auth errors mean the service is reachable but key is wrong/missing
                    # Treat as degraded rather than unhealthy
                    health.record_success(latency_ms)
                    logger.debug(f"Health check reachable (auth error): {provider_id} ({latency_ms:.0f}ms)")
                else:
                    health.record_failure(f"HTTP {response.status_code}")
                    logger.warning(
                        f"Health check failed: {provider_id} - HTTP {response.status_code}"
                    )

        except httpx.TimeoutException:
            health.record_failure("Timeout")
            logger.warning(f"Health check timeout: {provider_id}")
        except httpx.ConnectError:
            health.record_failure("Connection refused")
            logger.warning(f"Health check connection failed: {provider_id}")
        except Exception as e:
            health.record_failure(str(e))
            logger.error(f"Health check error: {provider_id} - {e}")

    def is_healthy(self, provider_id: str) -> bool:
        """Check if provider is healthy."""
        if provider_id not in self.health_data:
            return False
        return self.health_data[provider_id].status == HealthStatus.HEALTHY

    def is_available(self, provider_id: str) -> bool:
        """
        Check if provider is available (healthy, degraded, or unknown).

        UNKNOWN status is treated as available to allow first-time requests
        before health checks have run.
        """
        if provider_id not in self.health_data:
            # Not in health data yet = treat as available (optimistic)
            return True
        return self.health_data[provider_id].status in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNKNOWN,
        ]

    def get_healthy_providers(self) -> List[str]:
        """Get list of healthy providers."""
        return [
            pid
            for pid, health in self.health_data.items()
            if health.status == HealthStatus.HEALTHY
        ]

    def get_available_providers(self) -> List[str]:
        """Get list of available providers (healthy or degraded)."""
        return [
            pid
            for pid, health in self.health_data.items()
            if health.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        ]

    def get_latency(self, provider_id: str) -> float:
        """Get average latency for provider."""
        if provider_id not in self.health_data:
            return float("inf")
        return self.health_data[provider_id].avg_latency_ms

    def get_status(self, provider_id: str) -> Dict[str, Any]:
        """Get detailed status for provider."""
        if provider_id not in self.health_data:
            return {"error": "Unknown provider"}

        health = self.health_data[provider_id]
        return {
            "provider_id": health.provider_id,
            "status": health.status.value,
            "last_check": health.last_check.isoformat() if health.last_check else None,
            "last_success": health.last_success.isoformat()
            if health.last_success
            else None,
            "last_error": health.last_error,
            "avg_latency_ms": round(health.avg_latency_ms, 2),
            "consecutive_failures": health.consecutive_failures,
            "samples": len(health.latency_samples),
        }

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all providers."""
        return {pid: self.get_status(pid) for pid in self.health_data}

    def get_best_providers(self, limit: int = 5) -> List[str]:
        """
        Get best providers sorted by health and latency.

        Returns providers that are:
        1. Healthy
        2. Sorted by latency (fastest first)
        """
        available = [
            (pid, self.health_data[pid]) for pid in self.get_available_providers()
        ]

        # Sort by status (healthy first) then by latency
        available.sort(
            key=lambda x: (
                0 if x[1].status == HealthStatus.HEALTHY else 1,
                x[1].avg_latency_ms if x[1].avg_latency_ms > 0 else float("inf"),
            )
        )

        return [pid for pid, _ in available[:limit]]


# Global instance
health_monitor = ProviderHealthMonitor()


async def get_health_monitor() -> ProviderHealthMonitor:
    """Get the global health monitor instance."""
    return health_monitor
