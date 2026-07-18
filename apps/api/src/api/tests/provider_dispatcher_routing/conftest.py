"""
Shared stubs for ProviderDispatcher routing tests.

All tests use synthetic configs and stub providers injected via the
ProviderDispatcher(configs=..., class_map=...) constructor — no real
providers, no environment variables, no filesystem access (except where
explicitly testing env-var-based configuration).
"""

from __future__ import annotations

import os

from api.providers.base import BaseProvider, ProviderHealth, ProviderResult
from api.providers.dispatcher import ProviderDispatcher

# ── Stub provider ───────────────────────────────────────────────────────────


class _StubProvider(BaseProvider):
    """Minimal provider stub with configurable costs, model, and behavior.

    COST_* are class-level floats on BaseProvider — we set them as instance attrs
    so the dispatcher's ``_provider_costs()`` picks them up.
    """

    def __init__(self, provider_id: str, config: dict) -> None:
        super().__init__(provider_id, config)
        self.COST_INPUT_PER_1K = float(config.get("cost_input_per_1k", 0.0))
        self.COST_OUTPUT_PER_1K = float(config.get("cost_output_per_1k", 0.0))
        # force_fallback requires a sequence of fallback PIDs — stored in config
        self._fake_fail: bool = False
        self._fake_fail_error: str = "stub failure"
        self._fake_fail_category: str = "server-error"
        self._invoke_hook = None

    async def invoke(self, messages=None, model=None, **kwargs):
        if self._fake_fail:
            return ProviderResult(
                ok=False,
                provider=self.provider_id,
                model=model or self.default_model,
                error=self._fake_fail_error,
                error_category=self._fake_fail_category,
                latency_ms=1.0,
            )
        if self._invoke_hook:
            return await self._invoke_hook(messages, model, **kwargs)
        return ProviderResult(
            ok=True,
            text=f"ok from {self.provider_id}",
            provider=self.provider_id,
            model=model or self.default_model,
            usage={"input_tokens": 1, "output_tokens": 1},
            cost_usd=(self.COST_INPUT_PER_1K / 1000 * 1 + self.COST_OUTPUT_PER_1K / 1000 * 1),
            latency_ms=2.0,
        )

    async def stream(self, messages=None, model=None, **kwargs):
        return
        yield  # make it an async generator (unreachable, but syntactically required)

    async def health_check(self):
        return ProviderHealth(provider_id=self.provider_id, healthy=True)


# ── Dispatcher factory helpers ──────────────────────────────────────────────


def _make_dispatcher(providers: dict) -> ProviderDispatcher:
    """
    Build a ProviderDispatcher from a {provider_id: config_dict} mapping.

    Each config_dict may contain: cost_input_per_1k, cost_output_per_1k,
    priority_tier, tier, local_routing, capabilities, default_model, hidden.
    Sensible defaults are applied so ``is_configured()`` returns True for all
    entries (an api_key_env is set pointing to a stub env var that is set).
    """
    configs = {}
    for pid, cfg in providers.items():
        configs[pid] = {
            "name": pid,
            "endpoint": "http://stub",
            "priority_tier": cfg.get("priority_tier", 1),
            "tier": cfg.get("tier", "cloud"),
            "local_routing": cfg.get("local_routing", False),
            "capabilities": cfg.get("capabilities", ["chat"]),
            "default_model": cfg.get("default_model", "stub-model"),
            "cost_input_per_1k": cfg.get("cost_input_per_1k", 0.0),
            "cost_output_per_1k": cfg.get("cost_output_per_1k", 0.0),
            "hidden": cfg.get("hidden", False),
            "api_key_env": f"_TEST_KEY_{pid.upper()}",
        }
    # Set env vars so is_configured() returns True
    for pid in configs:
        os.environ[f"_TEST_KEY_{pid.upper()}"] = "stub-key"
    class_map = {pid: _StubProvider for pid in configs}
    return ProviderDispatcher(configs=configs, class_map=class_map)


def _clean_env(providers: dict) -> None:
    """Remove env vars set by _make_dispatcher."""
    for pid in providers:
        os.environ.pop(f"_TEST_KEY_{pid.upper()}", None)


# =============================================================================
# 1. Provider Selection
# =============================================================================
