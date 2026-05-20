"""
Provider health monitoring and metrics collection
"""

import asyncio
import time
from typing import Dict, List, Any
import httpx
from .config.providers import get_provider_settings
from .storage.cache import cache

# Health check configuration
HEALTH_CHECK_INTERVAL = 60  # seconds
PROVIDER_HEALTH_KEY = "provider_health_status"


class ProviderMonitor:
    def __init__(self):
        self._running = False
        self._task = None
        self._provider_status: Dict[str, Dict[str, Any]] = {}

    async def start(self):
        """Start the monitoring task"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        print("Provider monitor started")

    async def stop(self):
        """Stop the monitoring task"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("Provider monitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                await self._check_providers()
            except Exception as e:
                print(f"Error in provider monitor: {e}")
                # Re-raise to see the full traceback for debugging
                raise

            await asyncio.sleep(HEALTH_CHECK_INTERVAL)

    async def _check_providers(self):
        """Check health of all enabled providers"""
        providers = get_provider_settings()

        for provider in providers:
            if not provider["enabled"]:
                continue

            name = provider["name"]
            base_url = provider["base_url"]

            # Simple connectivity check
            status = await self._check_connectivity(base_url)

            self._provider_status[name] = {
                "status": "healthy" if status["ok"] else "unhealthy",
                "last_check": time.time(),
                "latency_ms": status.get("latency_ms", 0),
                "error": status.get("error"),
            }

        # Update cache with latest status
        await cache.set(
            PROVIDER_HEALTH_KEY, self._provider_status, expire=HEALTH_CHECK_INTERVAL * 2
        )

    async def _check_connectivity(self, url: str) -> Dict[str, Any]:
        """Check connectivity to a URL"""
        if not url:
            return {"ok": False, "error": "No URL provided"}

        # Don't actually call LLM APIs, just check if endpoint is reachable
        # For many providers, a simple GET to root or /health might fail or not exist
        # This is a heuristic check. For production, we might need provider-specific health endpoints.

        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=10.0) as client:
                # We expect 401/403 (auth error) or 404/405 (method not allowed) which means service is UP
                # Connection error or Timeout means service is DOWN
                try:
                    resp = await client.get(url)
                    latency = (time.time() - start_time) * 1000
                    return {"ok": True, "latency_ms": latency, "code": resp.status_code}
                except httpx.HTTPStatusError as e:
                    # Status codes are actually fine, it means server responded
                    latency = (time.time() - start_time) * 1000
                    return {
                        "ok": True,
                        "latency_ms": latency,
                        "code": e.response.status_code,
                    }
                except httpx.TimeoutException:
                    return {"ok": False, "error": "Timeout", "latency_ms": 10000}
                except httpx.ConnectError:
                    return {"ok": False, "error": "Connection failed", "latency_ms": 0}

        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def get_status(self) -> Dict[str, Any]:
        """Get current provider status"""
        # Try cache first
        cached = await cache.get(PROVIDER_HEALTH_KEY)
        if cached:
            return cached

        return self._provider_status


# Global monitor instance
monitor = ProviderMonitor()
