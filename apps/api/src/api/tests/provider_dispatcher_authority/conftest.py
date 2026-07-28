"""Shared fixtures for provider dispatcher authority tests."""

import asyncio
import sys
from pathlib import Path

import pytest

# Ensure the src root is on sys.path so `api.*` imports work from the split test package.
_pkg_root = str(Path(__file__).resolve().parents[3])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from api.providers.base import BaseProvider, ProviderHealth, ProviderResult


class StubProvider(BaseProvider):
    """A minimal provider stub that returns success by default."""

    async def invoke(self, messages=None, model=None, **kwargs):
        _ = messages, kwargs
        return ProviderResult(
            ok=True,
            provider=self.provider_id,
            model=model or "stub",
        )

    async def stream(self, messages=None, model=None, **kwargs):
        _ = messages, model, kwargs
        if kwargs.get("never", False):
            yield {}

    async def health_check(self):
        return ProviderHealth(provider_id=self.provider_id, healthy=True)


class WarmupProvider(StubProvider):
    """A provider stub that supports warmup."""

    async def warmup(self):
        await asyncio.sleep(0)
        return ProviderResult(
            ok=True,
            provider=self.provider_id,
            model=self.default_model or "stub",
            latency_ms=10.0,
        )


@pytest.fixture
def stub_provider():
    """Fixture that returns a StubProvider instance."""
    return StubProvider("stub", {"default_model": "stub-model"})


@pytest.fixture
def warmup_provider():
    """Fixture that returns a WarmupProvider instance."""
    return WarmupProvider("warmup", {"default_model": "warmup-model"})
