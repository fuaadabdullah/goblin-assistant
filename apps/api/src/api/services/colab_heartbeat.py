"""Dedicated heartbeat polling for the disposable Colab worker provider."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

import structlog

from api.providers.dispatcher import dispatcher
from api.services.provider_health import health_monitor

logger = structlog.get_logger(__name__)

_DEFAULT_INTERVAL_SECONDS = 60
_PROVIDER_ID = "gcp_vm"


def _env_true(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        parsed = int(raw.strip())
    except (TypeError, ValueError):
        return default
    return max(1, parsed)


class ColabHeartbeatService:
    def __init__(self, provider_id: str = _PROVIDER_ID) -> None:
        self.provider_id = provider_id
        self._running = False
        self._task: Optional[asyncio.Task[Any]] = None

    def _enabled(self) -> bool:
        return _env_true("COLAB_WORKER_HEARTBEAT_ENABLED", default=True)

    def _interval_seconds(self) -> int:
        return _env_positive_int(
            "COLAB_WORKER_HEARTBEAT_INTERVAL_SECONDS",
            _DEFAULT_INTERVAL_SECONDS,
        )

    async def _probe_if_configured(self) -> bool:
        if not dispatcher.get_provider_config(self.provider_id):
            return False
        if not dispatcher.is_configured(self.provider_id):
            return False
        await health_monitor.probe_provider(self.provider_id)
        return True

    async def start(self) -> None:
        if not self._enabled():
            logger.info("colab_heartbeat_disabled")
            return
        if self._running:
            return

        self._running = True
        try:
            await self._probe_if_configured()
        except Exception as exc:
            logger.warning("colab_heartbeat_initial_probe_failed", error=str(exc))

        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info(
            "colab_heartbeat_started",
            interval_seconds=self._interval_seconds(),
            provider_id=self.provider_id,
        )

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        logger.info("colab_heartbeat_stopped", provider_id=self.provider_id)

    async def _heartbeat_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self._interval_seconds())
            if not self._running:
                break
            try:
                await self._probe_if_configured()
            except Exception as exc:
                logger.warning("colab_heartbeat_probe_failed", error=str(exc))


colab_heartbeat = ColabHeartbeatService()
